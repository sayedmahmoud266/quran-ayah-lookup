---
name: contextual-semantic-vector-search
description: Used to add a contextual semantic vector search to quran-ayah-lookup
---

### Role
Act as an expert Python AI Engineer. Create a search wrapper for quran-ayah-lookup.

### Context:
- Use existing database of Quran verses as the corpus for semantic search.
- Use existing normalization function to preprocess verses for better matching or simply use the normalized text from the database.
- I want to use `sentence-transformers` (paraphrase-multilingual-MiniLM-L12-v2) and `FAISS` for semantic matching.

### Requirements:
1. **Indexing:** create a separate python script for indexing. it's sole purpose is to build the binary FAISS index.
On initialization, loop through the library's database, normalize each verse, and create a FAISS index. Store a mapping between the FAISS index and the library's (Surah, Ayah) identifiers.
save the index to disk for later use in the search function directly. save to (/src/resources/vector/faiss_index.bin) and the mapping to (/src/resources/vector/vindex_mapping.json).

2. **Expanding Window Search:**
   - Create a method `vector_search(query, normalize=False, treshold=0.7, surah_hint=None, start_after=None)`.
   - If `surah_hint` is given: First, search ONLY within that Surah's indices. 
   - If the best similarity score is < 0.7, automatically expand the search to `surah_hint +/- 1`, then `+/- 2`, until a confident match is found or the whole Quran is searched.
   - If `surah_hint` is not given, search the entire index from the start. If no match is found with a score >= 0.7, return an empty result.
   - If `normalize` is True, normalize the input query before searching. If False, use the raw input text for searching (not recommended for best results).

3. **Positional Prioritization:**
   - If `start_after` (tuple: surah, ayah) is provided, apply a "Gravity" effect: favor results that appear chronologically after this point by boosting their similarity score by 15% during the ranking phase.

4. **Sequence Detection:**
   - If the input `query` contains multiple verses, the search should identify the starting verse and return it along with the subsequent 2-3 verses from the library's database to match the user's input length.

5. **Output:** Return a MultiAyahMatch object containing the best matching verse(s) along with their similarity scores and identifiers.