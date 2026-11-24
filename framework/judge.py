"""Sets up the Ragas "judge": the Claude Sonnet LLM and the local embeddings model.
Why it exists: every LLM-based Ragas metric needs these two objects, and this is the
only file that knows how to build them (so changing the judge is a one-file change).
"""
from functools import lru_cache

import anthropic
import instructor
from ragas.cache import DiskCacheBackend
from ragas.embeddings import embedding_factory
from ragas.llms import llm_factory

from framework.config import CACHE_DIR, CONFIG, use_cache


@lru_cache(maxsize=1)
def judge_llm():
    """Claude Sonnet, wrapped for Ragas.
    - Ragas's built-in DiskCacheBackend saves every judge answer in .cache/ragas, so a
      repeat run costs nothing and gives identical scores. (--no-cache turns it off.)
    - We pass the plain SYNC Anthropic client; Ragas runs it in a thread for us.
    - mode=ANTHROPIC_TOOLS: Ragas's default instructor mode is not valid for Anthropic, so we
      ask for structured output through Claude's tool-calling instead.
    - We deliberately do NOT set temperature: current Claude models reject it, and Ragas
      already knows to leave it out for provider="anthropic"."""
    client = anthropic.Anthropic(max_retries=CONFIG["ragas"]["max_retries"], timeout=CONFIG["ragas"]["timeout"])
    cache = DiskCacheBackend(cache_dir=str(CACHE_DIR / "ragas")) if use_cache() else None
    return llm_factory(CONFIG["models"]["judge_llm"], provider="anthropic", client=client,
                       cache=cache, max_tokens=2048)


@lru_cache(maxsize=1)
def judge_embeddings():
    """The same local MiniLM model the bot uses for retrieval (free, no API key)."""
    return embedding_factory("huggingface", model=CONFIG["models"]["embeddings"])
