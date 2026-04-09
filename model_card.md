# DocuBot Model Card

This model card reflects the design and behavior of the DocuBot system after implementing retrieval and testing all three modes.

---

## 1. System Overview

**What is DocuBot trying to do?**
DocuBot is a question-answering system that uses project documentation to answer user queries. It aims to retrieve relevant information from documents and provide accurate, grounded responses while avoiding unsupported answers.

**What inputs does DocuBot take?**
DocuBot takes a user question as input, along with a folder of documentation files (`.md` or `.txt`). In RAG mode, it also uses an LLM (Gemini API) to generate answers based on retrieved content.

**What outputs does DocuBot produce?**
DocuBot produces either:

* Retrieved document snippets (retrieval-only mode), or
* A generated answer based on those snippets (RAG mode), or
* A refusal message when it lacks sufficient evidence.

---

## 2. Retrieval Design

**How does your retrieval system work?**

* Documents are split into paragraph-level sections using blank lines.
* Each section is tokenized, cleaned, and indexed in an inverted index mapping words to `(filename, section_id)`.
* Relevance is scored using a TF-IDF–style approach:

  * Term frequency (TF) counts word occurrences in a section.
  * Inverse document frequency (IDF) reduces weight of common words.
* Sections are ranked by score and the top results are returned.

**What tradeoffs did you make?**

* I chose paragraph-based splitting for simplicity and readability instead of more complex chunking.
* TF-IDF improves relevance over simple counting, but is still lightweight compared to embeddings.
* The system prioritizes simplicity and transparency over maximum accuracy.

---

## 3. Use of the LLM (Gemini)

**When does DocuBot call the LLM and when does it not?**

* **Naive LLM mode:**
  Sends the entire document corpus to the LLM and asks it to answer the question.

* **Retrieval only mode:**
  Does not use the LLM. Returns the most relevant document sections directly.

* **RAG mode:**
  Retrieves top sections first, then sends only those snippets to the LLM to generate a grounded answer.

**What instructions do you give the LLM to keep it grounded?**

* Only use the provided snippets to answer the question.
* Do not introduce external knowledge.
* If the answer cannot be found in the snippets, say:
  "I do not know based on the docs I have."
* Focus on accuracy over completeness.

---

## 4. Experiments and Comparisons

| Query                                      | Naive LLM: helpful or harmful? | Retrieval only: helpful or harmful? | RAG: helpful or harmful? | Notes                                                                                              |
| ------------------------------------------ | ------------------------------ | ----------------------------------- | ------------------------ | -------------------------------------------------------------------------------------------------- |
| Where is the auth token generated?         | Helpful but ungrounded         | Helpful and accurate                | Most helpful             | Naive sounded confident but didn’t show source. Retrieval showed exact section. RAG combined both. |
| How do I connect to the database?          | Mixed                          | Helpful                             | Most helpful             | Retrieval returned correct snippet but required interpretation. RAG explained it clearly.          |
| Which endpoint lists all users?            | Helpful but risky              | Helpful                             | Most helpful             | Naive could blend info. Retrieval showed exact endpoint. RAG summarized clearly.                   |
| How does a client refresh an access token? | Harmful                        | Neutral                             | Neutral                  | Docs lacked strong evidence. Naive guessed. Retrieval weak. RAG sometimes refused or failed.       |

**What patterns did you notice?**

* Naive LLM often sounds impressive but is not trustworthy because it does not clearly show evidence.
* Retrieval-only is the most reliable for correctness but harder to read.
* RAG provides the best balance when retrieval succeeds and the LLM is available.
* When retrieval is weak, all modes struggle, but naive mode is the most misleading.

---

## 5. Failure Cases and Guardrails

**Failure case 1**

* **Question:** How does a client refresh an access token?
* **What happened:** Naive LLM generated a confident answer even though the docs did not clearly support it.
* **What should have happened:** The system should have refused due to lack of strong evidence.

**Failure case 2**

* **Question:** Any query during RAG mode
* **What happened:** The Gemini API returned a 429 quota error and failed to generate a response.
* **What should have happened:** The system should fall back to retrieval-only mode or provide a graceful failure message.

**When should DocuBot say “I do not know based on the docs I have”?**

* When no relevant sections are retrieved for the query.
* When retrieved sections have very low relevance scores.
* When the query is unrelated to the documentation (e.g., weather or general knowledge questions).

**What guardrails did you implement?**

* A relevance threshold (`has_useful_context`) to ensure only meaningful results are used.
* Refusal when no sections meet the threshold.
* Limiting answers to retrieved snippets in RAG mode.
* Avoiding full-document generation in retrieval-based modes.

---

## 6. Limitations and Future Improvements

**Current limitations**

1. Retrieval is based on keyword matching and TF-IDF, which may miss semantic meaning.
2. The system depends on external LLM APIs, which can fail due to rate limits or availability.
3. Section-based splitting may not always capture the best context boundaries.

**Future improvements**

1. Use embeddings or vector databases for more semantic retrieval.
2. Add fallback logic when the LLM fails (e.g., automatically switch to retrieval-only mode).
3. Improve chunking strategy (e.g., overlapping windows or sentence-level splitting).

---

## 7. Responsible Use

**Where could this system cause real world harm if used carelessly?**

If DocuBot is used in critical domains (e.g., security, healthcare, or finance), incorrect or hallucinated answers could mislead users. Naive generation mode is especially risky because it can produce confident but unsupported information.

**What instructions would you give real developers who want to use DocuBot safely?**

* Always verify answers against the original documentation.
* Prefer retrieval-based or RAG modes over naive generation.
* Implement strict refusal rules when evidence is weak.
* Monitor API failures and add fallback behavior.

---
