# Metric cheat sheet

"HR docs" = the fictional Northwind Corp policies in `data/knowledge_base/`. Pass lines live in `config.yaml`.

## Retrieval: did the bot find the right pages?

### Context Precision ("Finds the right pages")
- **Asks:** Of the pages retrieved, are the relevant ones there, and ranked first?
- **Analogy:** A librarian hands you 3 books. Great if the right one is on top; poor if it is buried under two irrelevant ones.
- **Good:** Q "How many sick days?" -> top page is *Sick Leave - Sick days*. **Bad:** top pages are gym and home-office rules, sick leave is third.
- **Low score means:** slower, costlier, more error-prone answers.
- **Typical fix:** better chunking or embeddings, re-ranking, smaller top-k.

### Context Recall ("Finds ALL the needed pages")
- **Asks:** Is everything needed for the approved answer present in the retrieved pages?
- **Analogy:** Packing for a trip: did you bring *everything* on the checklist?
- **Good:** "15 vacation days + 10 sick days" question retrieves both the vacation and sick-leave pages. **Bad:** only the vacation page.
- **Low score means:** the bot answers without the key policy, so it guesses or gives half an answer.
- **Typical fix:** raise top-k, improve chunk size, fix missing or badly written policy content.

## Generation: is the answer grounded and on-topic?

### Faithfulness ("Sticks to the facts")
- **Asks:** Is every claim in the answer supported by the retrieved pages?
- **Analogy:** An open-book exam where you may only quote the book.
- **Good:** "Full-time employees get 15 vacation days." **Bad:** "...plus a free company car after two years" (not in any HR doc).
- **Low score means:** invented policies; HR and legal exposure.
- **Typical fix:** stricter prompt ("answer only from context, say you don't know"), guardrails.

### Answer Relevancy ("Answers the question asked")
- **Asks:** Does the answer address the question? (Ragas guesses the question the answer fits and compares it to the real one with embeddings.)
- **Analogy:** You ask the time and get a weather report.
- **Good:** Q sick days -> "10 paid sick days." **Bad:** Q sick days -> a description of the hybrid schedule (true but irrelevant).
- **Note:** an honest "I don't know" is scored as non-committal, so the unanswerable question is excluded here.
- **Low score means:** rambling or off-topic replies; employees stop trusting the bot.
- **Typical fix:** prompt design, shorter answers.

## Answer quality: does it match the approved answer?

### Factual Correctness ("Gets the facts right")
- **Asks:** Do the claims in the answer match the claims in the approved answer?
- **Analogy:** Marking a test against the answer key.
- **Good:** "15 vacation days." **Bad:** "30 vacation days." Also catches guessing on the stock-options question.
- **Low score means:** wrong numbers or rules told to employees.
- **Typical fix:** check retrieval and prompt; check the document itself is right.

### Semantic Similarity ("Means the same thing")
- **Asks:** Is the answer's meaning close to the approved answer, ignoring wording? (Embeddings only, no judge LLM.)
- **Analogy:** Two people describing the same film in different words.
- **Good:** "Up to 5 days roll over" vs "You can carry over a maximum of 5 days." **Bad:** an answer about a different topic.
- **Caveat:** it can miss a single wrong number; pair it with Factual Correctness.
- **Typical fix:** prompt and model choice.

### Noise Sensitivity ("Not distracted by junk") - LOWER IS BETTER
- **Asks:** When an irrelevant page is retrieved, does the answer wrongly use it?
- **Analogy:** A student who repeats a random sentence from the wrong chapter.
- **Good (0.0):** parental-leave answer ignores the gym page. **Bad:** "...and a $30 gym reimbursement while on leave."
- **Low score is good:** the pass line in config is a *maximum*.
- **Typical fix:** retrieval filtering (similarity cut-off), prompt.

## Non-LLM metrics: free, instant, deterministic (but weak for chat answers)
They compare words, not meaning, so they are *informational*: tested, but they do not decide the traffic light.

| Metric | What it does | Why it is weak/strict | Example |
|---|---|---|---|
| **BLEU** | Matching word sequences | Built for translation; different correct wording scores low | "Staff receive 15 days of vacation" vs "Full-time employees get 15 vacation days" scores low |
| **ROUGE-L** | Longest shared word sequence | Rewards copying; "30 days" vs "15 days" is one word apart, so it still scores high | wrong answer, high score |
| **Exact Match** | Identical text, else 0 | Very strict: "15 days." fails against "15 days". Run only on short-answer questions, with the bot told to reply with just the value | "15 days" = "15 days" -> 1.0 |
| **String Similarity** | Letter-by-letter edit distance | Sees characters, not meaning | good for codes and IDs, poor for sentences |
