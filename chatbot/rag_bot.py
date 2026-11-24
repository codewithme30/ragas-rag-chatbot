"""The chatbot we are testing: a tiny RAG bot for Northwind Corp's HR policies.
Flow: load docs -> split into chunks -> embed -> find top-k for the question -> ask Claude.
Plain Python on purpose (no LangChain), so a new hire can read it in five minutes.
"""
import hashlib
import json
import random
from functools import lru_cache

import anthropic
import numpy as np
from sentence_transformers import SentenceTransformer

from framework.config import CACHE_DIR, CONFIG, ROOT, bot_mode, use_cache

GOOD_PROMPT = (
    "You are an HR assistant for Northwind Corp. Answer ONLY from the context provided. "
    "If the answer is not in the context, reply exactly: I don't know based on the HR documents. "
    "Keep the answer to one or two short sentences."
)
# Buggy mode: the prompt now ALLOWS guessing, which invites made-up policies.
BUGGY_PROMPT = (
    "You are a confident HR assistant for Northwind Corp. Always give a helpful, specific answer. "
    "If the context does not help, use your best guess. Never say you don't know. "
    "Keep the answer to one or two short sentences."
)
SHORT_HINT = " Reply with ONLY the final value, no full sentence. Example: 15 days"


# ---- Steps 1-2: load the documents and split them into chunks -------------------------
def split_into_chunks(text: str, max_chars: int) -> list[str]:
    """One chunk per '## section' (prefixed with the doc title). Very long ones are cut by size."""
    title, *sections = text.split("\n## ")
    title = title.lstrip("# ").strip()
    chunks = []
    for section in sections:
        chunk = f"{title} - {section.strip()}"
        chunks += [chunk[i:i + max_chars] for i in range(0, len(chunk), max_chars)]
    return chunks


@lru_cache(maxsize=1)
def load_chunks() -> list[str]:
    """Read every .md file in data/knowledge_base and chunk it."""
    chunks = []
    for path in sorted((ROOT / "data" / "knowledge_base").glob("*.md")):
        chunks += split_into_chunks(path.read_text(encoding="utf-8"), CONFIG["bot"]["chunk_size"])
    return chunks


# ---- Step 3: embeddings (local, free) ---------------------------------------------------
@lru_cache(maxsize=1)
def embedder() -> SentenceTransformer:
    return SentenceTransformer(CONFIG["models"]["embeddings"])


@lru_cache(maxsize=1)
def chunk_vectors() -> np.ndarray:
    """Turn every chunk into a vector once. Normalised, so cosine similarity = dot product."""
    return embedder().encode(load_chunks(), normalize_embeddings=True)


# ---- Step 4: retrieve the top-k most similar chunks -----------------------------------
def retrieve(question: str, k: int) -> list[str]:
    chunks = load_chunks()
    if bot_mode() == "buggy":  # BUG ON PURPOSE: random chunks instead of the best ones
        return random.Random(question).sample(chunks, k)
    q_vec = embedder().encode([question], normalize_embeddings=True)[0]
    scores = chunk_vectors() @ q_vec               # cosine similarity with every chunk
    return [chunks[i] for i in np.argsort(-scores)[:k]]  # best first


# ---- Steps 5-6: ask Claude Haiku and return the answer + the contexts ------------------
def ask(question: str, short: bool = False) -> dict:
    """Answer one question. Returns {"answer": str, "contexts": [str, ...]}.
    short=True asks for a bare value like '15 days' (used by the Exact Match test)."""
    model = CONFIG["models"]["bot_llm"]
    prompt = (BUGGY_PROMPT if bot_mode() == "buggy" else GOOD_PROMPT) + (SHORT_HINT if short else "")
    contexts = retrieve(question, CONFIG["bot"]["top_k"])

    # Disk cache: same question + model + mode + prompt + contexts => same saved answer.
    key = hashlib.sha256(json.dumps([question, model, bot_mode(), prompt, contexts]).encode()).hexdigest()
    cache_file = CACHE_DIR / "bot" / f"{key}.json"
    if use_cache() and cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))

    context_text = "\n\n".join(f"[{i + 1}] {c}" for i, c in enumerate(contexts))
    reply = anthropic.Anthropic().messages.create(
        model=model, max_tokens=300, system=prompt,
        messages=[{"role": "user", "content": f"Context:\n{context_text}\n\nQuestion: {question}"}],
    )
    result = {"answer": reply.content[0].text.strip(), "contexts": contexts}

    if use_cache():
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
