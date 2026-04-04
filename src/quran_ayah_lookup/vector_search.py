"""
Hybrid semantic search for Quran Ayah Lookup.

Two retrieval modes are supported, selectable via the ``asymmetric`` parameter:

**Asymmetric mode** (default, ``asymmetric=True``):
    Uses ``intfloat/multilingual-e5-base`` — an asymmetric model that requires
    different text prefixes for queries and passages.  Combined with BM25Okapi via
    Reciprocal Rank Fusion (RRF) for improved exact-term recall.

**Symmetric mode** (``asymmetric=False``):
    Uses ``paraphrase-multilingual-MiniLM-L12-v2`` — a symmetric model where queries
    and passages are encoded identically (no prefix needed).  Suitable for
    paraphrase-style queries.  FAISS-only (no BM25 fusion).

Architecture
------------
- **Dense retrieval** (FAISS ``IndexFlatIP``):
  L2-normalised embeddings → cosine similarity via inner product.

- **Lexical retrieval** (BM25Okapi, asymmetric mode only):
  Forces exact Arabic word recall for terms that semantics might miss.

- **Reciprocal Rank Fusion** (RRF, k=60, asymmetric mode only):
  Merges dense and lexical ranked lists purely by ordinal rank.

Requires the optional [vector] extras::

    pip install "quran-ayah-lookup[vector]"

And pre-built indexes::

    python scripts/build_vector_index.py

Example usage::

    from quran_ayah_lookup import vector_search

    # Asymmetric (default)
    result = vector_search("ٱلۡحَمۡدُ لِلَّهِ رَبِّ ٱلۡعَـٰلَمِينَ")
    print(result.get_reference())   # "1:2"

    # Symmetric
    result = vector_search("الله لا إله إلا هو", asymmetric=False)
    print(result.get_reference())   # "2:255"
"""

import json
import math
import os
import pickle
from collections import defaultdict
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import MultiAyahMatch, QuranDatabase, QuranVerse


# ---------------------------------------------------------------------------
# Paths to pre-built index files (relative to this source file)
# ---------------------------------------------------------------------------
_RESOURCES_DIR = os.path.join(os.path.dirname(__file__), "resources", "vector")

# Asymmetric index (intfloat/multilingual-e5-base + BM25)
_INDEX_PATH = os.path.join(_RESOURCES_DIR, "faiss_index.bin")
_MAPPING_PATH = os.path.join(_RESOURCES_DIR, "vindex_mapping.json")
_BM25_PATH = os.path.join(_RESOURCES_DIR, "bm25_index.pkl")
_MODEL_NAME = "intfloat/multilingual-e5-base"

# Symmetric index (paraphrase-multilingual-MiniLM-L12-v2)
_SYM_INDEX_PATH = os.path.join(_RESOURCES_DIR, "faiss_sym_index.bin")
_SYM_MAPPING_PATH = os.path.join(_RESOURCES_DIR, "vindex_sym_mapping.json")
_SYM_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

# RRF constant (Cormack 2009, also the Elasticsearch default)
_RRF_K = 60


# ---------------------------------------------------------------------------
# VectorSearch class
# ---------------------------------------------------------------------------

class VectorSearch:
    """
    Dual-mode semantic search over the Quran corpus.

    Loads pre-built FAISS indexes from disk.  Two retrieval modes are available:

    * **Asymmetric** (default): ``intfloat/multilingual-e5-base`` + BM25 + RRF.
      Best for recall of exact terms and paraphrases.
    * **Symmetric**: ``paraphrase-multilingual-MiniLM-L12-v2``, FAISS only.
      Lightweight alternative for paraphrase-style queries.

    Args:
        db: Optional pre-loaded :class:`~quran_ayah_lookup.models.QuranDatabase`.
            If omitted, the default database is loaded via
            :func:`~quran_ayah_lookup.loader.get_quran_database`.

    Raises:
        ImportError: If ``sentence-transformers``, ``faiss``, or ``rank-bm25``
            are not installed.
        FileNotFoundError: If the index files have not been built yet.
    """

    def __init__(self, db: Optional["QuranDatabase"] = None) -> None:
        # --- dependency check ---
        try:
            import faiss          # noqa: F401
            import numpy          # noqa: F401
            import rank_bm25      # noqa: F401
            import sentence_transformers  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "Hybrid vector search requires optional dependencies. Install them with:\n"
                '    pip install "quran-ayah-lookup[vector]"'
            ) from exc

        # --- index files check (all five must exist) ---
        all_paths = (_INDEX_PATH, _MAPPING_PATH, _BM25_PATH, _SYM_INDEX_PATH, _SYM_MAPPING_PATH)
        missing = [p for p in all_paths if not os.path.isfile(p)]
        if missing:
            raise FileNotFoundError(
                "Vector index files not found. Build them first by running:\n"
                "    python scripts/build_vector_index.py\n"
                f"Missing:\n" + "\n".join(f"  {p}" for p in missing)
            )

        import faiss as _faiss

        # --- asymmetric index (e5-base + BM25) ---
        self._index = _faiss.read_index(_INDEX_PATH)

        with open(_MAPPING_PATH, "r", encoding="utf-8") as fh:
            self._mapping: List[dict] = json.load(fh)

        with open(_BM25_PATH, "rb") as fh:
            self._bm25 = pickle.load(fh)

        # --- symmetric index (MiniLM) ---
        self._sym_index = _faiss.read_index(_SYM_INDEX_PATH)

        with open(_SYM_MAPPING_PATH, "r", encoding="utf-8") as fh:
            self._sym_mapping: List[dict] = json.load(fh)

        # Models are lazy-loaded on first search call
        self._model = None      # e5-base (asymmetric)
        self._sym_model = None  # MiniLM (symmetric)

        # Database
        if db is not None:
            self._db: "QuranDatabase" = db
        else:
            from .loader import get_quran_database
            self._db = get_quran_database()

    # ------------------------------------------------------------------
    # Model helpers
    # ------------------------------------------------------------------

    def _get_model(self):
        """Lazy-load intfloat/multilingual-e5-base."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(_MODEL_NAME)
        return self._model

    def _get_sym_model(self):
        """Lazy-load paraphrase-multilingual-MiniLM-L12-v2."""
        if self._sym_model is None:
            from sentence_transformers import SentenceTransformer
            self._sym_model = SentenceTransformer(_SYM_MODEL_NAME)
        return self._sym_model

    # ------------------------------------------------------------------
    # Encoding helpers
    # ------------------------------------------------------------------

    def _encode_query(self, text: str):
        """
        Encode a query for the **asymmetric** e5-base index.

        Prepends ``"query: "`` (required by the asymmetric model) and L2-normalises.
        """
        import numpy as np

        model = self._get_model()
        embedding = model.encode(
            ["query: " + text], convert_to_numpy=True, normalize_embeddings=True
        ).astype("float32")
        norm = embedding[0].dot(embedding[0]) ** 0.5
        if norm > 0:
            embedding = embedding / norm
        return embedding

    def _encode_symmetric(self, text: str):
        """
        Encode a query for the **symmetric** MiniLM index.

        No prefix needed — query and passage are encoded identically.
        """
        import numpy as np

        model = self._get_sym_model()
        embedding = model.encode(
            [text], convert_to_numpy=True, normalize_embeddings=True
        ).astype("float32")
        norm = embedding[0].dot(embedding[0]) ** 0.5
        if norm > 0:
            embedding = embedding / norm
        return embedding

    # ------------------------------------------------------------------
    # Candidate-building helpers
    # ------------------------------------------------------------------

    def _build_candidates_asymmetric(
        self, search_query: str, semantic_only: bool = False
    ) -> Tuple[List[Tuple[float, int, int]], Dict[Tuple[int, int], float]]:
        """
        FAISS + BM25 + RRF ranked candidates.  When *semantic_only* is ``True``,
        BM25 is skipped and ranking is by FAISS cosine score only (via single-list RRF).

        Returns:
            ``(candidates, faiss_score_map)`` where *candidates* is a list of
            ``(rrf_score, surah, ayah)`` tuples sorted descending, and
            *faiss_score_map* maps ``(surah, ayah)`` to raw FAISS cosine score.
        """
        query_vec = self._encode_query(search_query)
        raw_scores, ids = self._index.search(query_vec, k=self._index.ntotal)
        raw_scores = raw_scores[0].tolist()
        ids = ids[0].tolist()

        faiss_score_map: Dict[Tuple[int, int], float] = {}
        faiss_ranked: List[Tuple[int, int]] = []

        for score, vid in zip(raw_scores, ids):
            if vid < 0 or vid >= len(self._mapping):
                continue
            entry = self._mapping[vid]
            key = (entry["surah"], entry["ayah"])
            faiss_score_map[key] = float(score)
            faiss_ranked.append(key)

        if semantic_only:
            candidates = self._rrf_fuse(faiss_ranked)
        else:
            bm25_ranked = self._bm25_search(search_query)
            candidates = self._rrf_fuse(faiss_ranked, bm25_ranked)
        return candidates, faiss_score_map

    def _build_candidates_symmetric(
        self, search_query: str
    ) -> Tuple[List[Tuple[float, int, int]], Dict[Tuple[int, int], float]]:
        """
        FAISS (MiniLM, no prefix, no BM25) → candidates.

        Returns:
            ``(candidates, faiss_score_map)`` where *candidates* is a list of
            ``(rrf_score, surah, ayah)`` tuples (RRF over a single list) sorted
            descending, and *faiss_score_map* maps ``(surah, ayah)`` to the raw
            FAISS cosine score.
        """
        query_vec = self._encode_symmetric(search_query)
        raw_scores, ids = self._sym_index.search(query_vec, k=self._sym_index.ntotal)
        raw_scores = raw_scores[0].tolist()
        ids = ids[0].tolist()

        faiss_score_map: Dict[Tuple[int, int], float] = {}
        faiss_ranked: List[Tuple[int, int]] = []

        for score, vid in zip(raw_scores, ids):
            if vid < 0 or vid >= len(self._sym_mapping):
                continue
            entry = self._sym_mapping[vid]
            key = (entry["surah"], entry["ayah"])
            faiss_score_map[key] = float(score)
            faiss_ranked.append(key)

        candidates = self._rrf_fuse(faiss_ranked)  # single list, no BM25
        return candidates, faiss_score_map

    # ------------------------------------------------------------------
    # Other private helpers
    # ------------------------------------------------------------------

    def _bm25_search(self, query_text: str) -> List[Tuple[int, int]]:
        """
        Run BM25 retrieval and return ``(surah, ayah)`` tuples sorted by score.

        Only verses with a **positive** BM25 score are included.
        """
        import numpy as np

        tokens = query_text.split()
        if not tokens:
            return []
        scores = self._bm25.get_scores(tokens)
        order = np.argsort(-scores)
        return [
            (self._mapping[i]["surah"], self._mapping[i]["ayah"])
            for i in order
            if scores[i] > 0
        ]

    @staticmethod
    def _rrf_fuse(
        *ranked_lists: List[Tuple[int, int]], k: int = _RRF_K
    ) -> List[Tuple[float, int, int]]:
        """
        Reciprocal Rank Fusion over one or more ranked result lists.

        Args:
            *ranked_lists: Each list is a sequence of ``(surah, ayah)`` tuples
                sorted best-first.
            k: RRF damping constant (default 60).

        Returns:
            ``[(rrf_score, surah, ayah), ...]`` sorted descending by RRF score.
        """
        scores: Dict[Tuple[int, int], float] = defaultdict(float)
        for ranked in ranked_lists:
            for rank, (s, a) in enumerate(ranked, start=1):
                scores[(s, a)] += 1.0 / (k + rank)
        return sorted(
            [(sc, s, a) for (s, a), sc in scores.items()],
            key=lambda x: x[0],
            reverse=True,
        )

    @staticmethod
    def _is_after(surah: int, ayah: int, start_after: Tuple[int, int]) -> bool:
        """Return True if *(surah, ayah)* comes chronologically after *start_after*."""
        s0, a0 = start_after
        return surah > s0 or (surah == s0 and ayah > a0)

    def _get_next_verses(
        self, surah: int, ayah: int, count: int
    ) -> List["QuranVerse"]:
        """Return up to *count* verses immediately following *(surah, ayah)*."""
        ref_list = self._db.sorted_ayahs_ref_list
        try:
            idx = ref_list.index((surah, ayah))
        except ValueError:
            return []
        result: List["QuranVerse"] = []
        for i in range(idx + 1, min(idx + 1 + count, len(ref_list))):
            s, a = ref_list[i]
            try:
                result.append(self._db.get_verse(s, a))
            except (ValueError, KeyError):
                pass
        return result

    def _select_best(
        self,
        candidates: List[Tuple[float, int, int]],
        threshold: float,
        surah_hint: Optional[int],
        faiss_score_map: Dict[Tuple[int, int], float],
    ) -> Optional[Tuple[float, int, int]]:
        """
        Pick the highest-RRF-ranked candidate whose FAISS cosine score meets *threshold*.

        Threshold is applied to the raw FAISS cosine score (not the RRF score).
        If *surah_hint* is given, uses an expanding window search.

        Returns ``(rrf_score, surah, ayah)`` or ``None``.
        """
        if not candidates:
            return None

        def _passes(s: int, a: int) -> bool:
            return faiss_score_map.get((s, a), 0.0) >= threshold

        if surah_hint is None:
            best = candidates[0]
            return best if _passes(best[1], best[2]) else None

        # Expanding window
        expansion = 0
        while True:
            lo = max(1, surah_hint - expansion)
            hi = min(114, surah_hint + expansion)

            for rrf_score, s, a in candidates:
                if lo <= s <= hi:
                    if _passes(s, a):
                        return (rrf_score, s, a)
                    break  # best in window is below threshold

            if lo == 1 and hi == 114:
                break
            expansion += 1

        # Full expansion exhausted — return best overall if it passes threshold
        best = candidates[0]
        return best if _passes(best[1], best[2]) else None

    @staticmethod
    def _empty_match(query_text: str = "") -> "MultiAyahMatch":
        """Return an empty :class:`MultiAyahMatch` signalling *no result found*."""
        from .models import MultiAyahMatch
        return MultiAyahMatch(
            verses=[],
            similarity=0.0,
            matched_text="",
            query_text=query_text,
            start_surah=0,
            start_ayah=0,
            start_word=0,
            end_surah=0,
            end_ayah=0,
            end_word=0,
        )

    # ------------------------------------------------------------------
    # Public search method
    # ------------------------------------------------------------------

    def vector_search(
        self,
        query: str,
        normalize: bool = False,
        threshold: float = 0.7,
        surah_hint: Optional[int] = None,
        start_after: Optional[Tuple[int, int]] = None,
        asymmetric: bool = True,
        semantic_only: bool = False,
    ) -> "MultiAyahMatch":
        """
        Perform semantic search over the Quran corpus.

        Args:
            query:
                Arabic text to search for.
            normalize:
                If ``True``, strip diacritics from *query* before searching.
            threshold:
                Minimum **FAISS cosine similarity** (0.0–1.0) required to accept a
                match.  Default ``0.7``.
            surah_hint:
                If given, the search first checks only this surah, expanding to
                ``surah_hint ± 1``, then ``± 2``, until a confident match is found
                or the whole Quran has been searched.
            start_after:
                ``(surah, ayah)`` gravity anchor.  Verses appearing *after* this
                position receive a 15 % boost to their RRF/rank score during ranking
                (gravity affects ranking only; reported similarity is always the raw
                FAISS cosine score).
            asymmetric:
                If ``True`` (default), use the asymmetric ``intfloat/multilingual-e5-base``
                model with BM25 + RRF fusion.  If ``False``, use the symmetric
                ``paraphrase-multilingual-MiniLM-L12-v2`` model with FAISS only.
            semantic_only:
                If ``True``, skip BM25 lexical retrieval and RRF fusion even in
                asymmetric mode, using pure FAISS cosine ranking instead.  Has no
                effect when ``asymmetric=False`` (symmetric mode is already FAISS-only).
                Default ``False``.

        Returns:
            :class:`~quran_ayah_lookup.models.MultiAyahMatch` containing the best
            matching verse(s), ``start_word`` / ``end_word`` for partial ayah matches,
            and ``similarity`` on a 0–100 scale (raw FAISS cosine × 100).

            If no match meets *threshold*, an empty ``MultiAyahMatch``
            (``verses=[]``, ``similarity=0.0``) is returned.
        """
        from .models import MultiAyahMatch
        from .text_utils import fuzzy_substring_search, normalize_arabic_text

        if not query or not query.strip():
            return self._empty_match(query)

        # 1. Optionally normalise the query
        search_query = normalize_arabic_text(query) if normalize else query

        # 2. Check index is non-empty
        total = self._index.ntotal if asymmetric else self._sym_index.ntotal
        if total == 0:
            return self._empty_match(query)

        # 3. Build candidates using selected retrieval mode
        if asymmetric:
            candidates, faiss_score_map = self._build_candidates_asymmetric(search_query, semantic_only=semantic_only)
        else:
            candidates, faiss_score_map = self._build_candidates_symmetric(search_query)

        if not candidates:
            return self._empty_match(query)

        # 4. Apply gravity — boost scores 15 % for verses after start_after
        if start_after is not None:
            candidates = [
                (
                    rrf * 1.15 if self._is_after(s, a, start_after) else rrf,
                    s,
                    a,
                )
                for rrf, s, a in candidates
            ]
            candidates.sort(key=lambda x: x[0], reverse=True)

        # 5. Select the best candidate (expanding window if surah_hint is set)
        #    Threshold applies to FAISS cosine score, not to the RRF/rank score.
        best = self._select_best(candidates, threshold, surah_hint, faiss_score_map)
        if best is None:
            return self._empty_match(query)

        _, best_surah, best_ayah = best
        raw_similarity = faiss_score_map.get((best_surah, best_ayah), 0.0)

        # 6. Fetch the matched verse from the database
        try:
            best_verse = self._db.get_verse(best_surah, best_ayah)
        except (ValueError, KeyError):
            return self._empty_match(query)

        verse_words = best_verse.text_normalized.split()
        query_words = search_query.split()

        # 7. Partial-ayah detection
        is_partial = len(query_words) < len(verse_words) * 0.85

        if is_partial:
            fsr = fuzzy_substring_search(
                search_query,
                best_verse.text_normalized,
                threshold=0.5,
            )
            if fsr:
                start_word: int = fsr["start_word"]
                end_word: int = fsr["end_word"]
            else:
                start_word = 0
                end_word = min(len(query_words), len(verse_words))
        else:
            start_word = 0
            end_word = len(verse_words)

        # 8. Sequence detection
        verses: List["QuranVerse"] = [best_verse]
        end_surah = best_surah
        end_ayah = best_ayah
        final_end_word = end_word

        if len(query_words) > len(verse_words) * 1.3:
            extra_count = min(
                3,
                math.ceil(
                    (len(query_words) - len(verse_words)) / max(len(verse_words), 1)
                ),
            )
            extra_verses = self._get_next_verses(best_surah, best_ayah, extra_count)
            verses.extend(extra_verses)
            if extra_verses:
                last = extra_verses[-1]
                end_surah = last.surah_number
                end_ayah = last.ayah_number
                final_end_word = len(last.text_normalized.split())

        # 9. Build matched_text
        if is_partial and len(verses) == 1:
            matched_text = " ".join(verse_words[start_word:end_word])
        else:
            matched_text = " ".join(v.text_normalized for v in verses)

        return MultiAyahMatch(
            verses=verses,
            similarity=round(raw_similarity * 100, 2),
            matched_text=matched_text,
            query_text=search_query,
            start_surah=best_surah,
            start_ayah=best_ayah,
            start_word=start_word,
            end_surah=end_surah,
            end_ayah=end_ayah,
            end_word=final_end_word,
        )


# ---------------------------------------------------------------------------
# Module-level singleton + convenience function
# ---------------------------------------------------------------------------

_default_vs: Optional[VectorSearch] = None


def vector_search(
    query: str,
    normalize: bool = False,
    threshold: float = 0.7,
    surah_hint: Optional[int] = None,
    start_after: Optional[Tuple[int, int]] = None,
    asymmetric: bool = True,
    semantic_only: bool = False,
) -> "MultiAyahMatch":
    """
    Module-level convenience wrapper around :meth:`VectorSearch.vector_search`.

    Lazily creates a single :class:`VectorSearch` instance on the first call
    and reuses it for subsequent calls.

    Args:
        query: Arabic text to search for.
        normalize: Normalise diacritics in *query* before searching.
        threshold: Minimum FAISS cosine similarity (0.0–1.0).
        surah_hint: Restrict initial search to this surah (expands outward).
        start_after: ``(surah, ayah)`` gravity anchor.
        asymmetric: If ``True`` (default), use e5-base + BM25 + RRF.
            If ``False``, use MiniLM (FAISS only, symmetric).
        semantic_only: If ``True``, skip BM25 and RRF even in asymmetric mode
            (pure FAISS cosine ranking).  Default ``False``.

    Returns:
        :class:`~quran_ayah_lookup.models.MultiAyahMatch`

    Raises:
        ImportError: If ``sentence-transformers``, ``faiss``, or ``rank-bm25``
            are not installed.
        FileNotFoundError: If the vector indexes have not been built yet.
    """
    global _default_vs
    if _default_vs is None:
        _default_vs = VectorSearch()
    return _default_vs.vector_search(
        query,
        normalize=normalize,
        threshold=threshold,
        surah_hint=surah_hint,
        start_after=start_after,
        asymmetric=asymmetric,
        semantic_only=semantic_only,
    )
