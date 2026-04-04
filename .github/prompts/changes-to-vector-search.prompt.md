---
name: changes-to-vector-search
description: Changes to vector search
---

# Changes to Vector Search Implementation
1. Use an assymetric retrieval model instead of a symmetric one. The search function will now be called `vector_search` instead of `find_verse` to reflect its broader capabilities. ('intfloat/multilingual-e5-base' instead of 'paraphrase-multilingual-MiniLM-L12-v2')
2. update both the indexing script and the search function to use the new model and its specific requirements (e.g., tokenization, embedding dimensions).
3. implement a hybrid search:
Relying 100% on dense vectors for the Quran is risky because the vocabulary is highly repetitive, causing vectors to overlap. The industry standard for this is Hybrid Search:
- Lexical (BM25): Use a library like rank_bm25. It is a lightning-fast, traditional search engine that forces the system to respect the exact words (like "زكريا" or "الفلق").
- Semantic (FAISS): You use your vector search to handle the spelling mistakes and missing words.
- Reciprocal Rank Fusion (RRF): You combine the scores of both. If a verse has the exact word and the semantic meaning, it shoots to the top.