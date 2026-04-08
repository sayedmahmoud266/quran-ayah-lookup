"""
Unit tests for vector_search.py and scripts/build_vector_index.py.

The tests use object.__new__ and manual attribute injection to bypass the
heavy faiss / sentence-transformers dependencies.  This means the tests run
correctly even when the [vector] extras are not installed.

Tests that exercise the actual imports (ImportError / FileNotFoundError guards)
use sys.modules patching to simulate the presence or absence of optional deps.
"""

import json
import math
import os
import sys
import types
from typing import List
from unittest.mock import MagicMock, call, mock_open, patch

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Ensure the src layout is importable
# ---------------------------------------------------------------------------
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "src"),
)

from quran_ayah_lookup.vector_search import VectorSearch, _MODEL_NAME, _SYM_MODEL_NAME
from quran_ayah_lookup.models import MultiAyahMatch, QuranVerse
from quran_ayah_lookup.loader import get_quran_database


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_verse(surah: int, ayah: int, text_normalized: str) -> QuranVerse:
    """Create a minimal QuranVerse for testing."""
    return QuranVerse(
        surah_number=surah,
        ayah_number=ayah,
        text=text_normalized,          # simplified: same as normalized for tests
        text_normalized=text_normalized,
        is_basmalah=False,
    )


def _make_fake_db(verses: List[QuranVerse]):
    """Build a thin mock QuranDatabase containing *verses*."""
    db = MagicMock()
    db.sorted_ayahs_ref_list = [(v.surah_number, v.ayah_number) for v in verses]
    verse_map = {(v.surah_number, v.ayah_number): v for v in verses}

    def _get_verse(s, a):
        if (s, a) not in verse_map:
            raise ValueError(f"Verse {s}:{a} not found")
        return verse_map[(s, a)]

    db.get_verse.side_effect = _get_verse
    db.get_all_verses.return_value = verses
    return db


def _make_vs(
    mapping: List[dict],
    scores: List[float],
    ids: List[int],
    db=None,
    encode_vec: np.ndarray = None,
    bm25_scores: np.ndarray = None,
) -> VectorSearch:
    """
    Instantiate VectorSearch WITHOUT calling __init__ and inject fake internals.
    This avoids the need for faiss / sentence-transformers to be installed.
    """
    vs: VectorSearch = object.__new__(VectorSearch)

    # Mock FAISS index
    mock_index = MagicMock()
    mock_index.ntotal = len(mapping)
    mock_index.search.return_value = (
        np.array([scores], dtype=np.float32),
        np.array([ids], dtype=np.int64),
    )
    vs._index = mock_index
    vs._mapping = mapping
    vs._model = MagicMock()  # lazy model already "loaded"

    if encode_vec is None:
        encode_vec = np.ones((1, 768), dtype=np.float32)  # e5-base dim
    vs._encode_query = MagicMock(return_value=encode_vec)

    # Mock BM25 index (all-zeros = no lexical signal; FAISS dominates)
    mock_bm25 = MagicMock()
    if bm25_scores is None:
        bm25_scores = np.zeros(len(mapping), dtype=np.float64)
    mock_bm25.get_scores.return_value = bm25_scores
    vs._bm25 = mock_bm25

    # Mock symmetric FAISS index (same scores/ids as asymmetric by default)
    mock_sym_index = MagicMock()
    mock_sym_index.ntotal = len(mapping)
    mock_sym_index.search.return_value = (
        np.array([scores], dtype=np.float32),
        np.array([ids], dtype=np.int64),
    )
    vs._sym_index = mock_sym_index
    vs._sym_mapping = mapping  # same mapping content
    vs._sym_model = MagicMock()
    vs._sym_model.encode.return_value = np.ones((1, 384), dtype=np.float32)

    if db is None:
        # Build a minimal 3-verse corpus used by most tests
        verses = [
            _make_verse(1, 1, "بسم الله الرحمن الرحيم"),
            _make_verse(1, 2, "الحمد لله رب العالمين"),
            _make_verse(2, 255, (
                "الله لا اله الا هو الحي القيوم لا تاخذه سنة ولا نوم"
                " له ما في السماوات وما في الارض"
            )),
        ]
        db = _make_fake_db(verses)
    vs._db = db

    return vs


# ---------------------------------------------------------------------------
# 1. ImportError guard (missing optional deps)
# ---------------------------------------------------------------------------

class TestImportGuards:

    def test_missing_deps_raises_import_error(self):
        """VectorSearch.__init__ raises ImportError when faiss not installed."""
        with patch.dict(sys.modules, {"faiss": None, "rank_bm25": None}):
            with pytest.raises(ImportError, match="pip install"):
                VectorSearch()

    def test_import_error_message_contains_pip_command(self):
        """The ImportError message tells the user how to fix it."""
        with patch.dict(sys.modules, {"faiss": None, "rank_bm25": None}):
            try:
                VectorSearch()
            except ImportError as exc:
                assert "quran-ayah-lookup[vector]" in str(exc)

    def test_missing_index_file_raises_file_not_found(self, tmp_path):
        """VectorSearch.__init__ raises FileNotFoundError when index files are absent."""
        # Provide faiss / sentence_transformers / rank_bm25 as stubs
        fake_faiss = types.ModuleType("faiss")
        fake_faiss.read_index = MagicMock()
        fake_st = types.ModuleType("sentence_transformers")
        fake_bm25_mod = types.ModuleType("rank_bm25")
        fake_bm25_mod.BM25Okapi = MagicMock()

        # Access the real module (not the shadowed function in quran_ayah_lookup namespace)
        vs_mod = sys.modules["quran_ayah_lookup.vector_search"]

        with patch.dict(
            sys.modules,
            {
                "faiss": fake_faiss,
                "sentence_transformers": fake_st,
                "rank_bm25": fake_bm25_mod,
                "numpy": np,
            },
        ):
            with patch.object(vs_mod, '_INDEX_PATH', str(tmp_path / "nonexistent.bin")), \
                 patch.object(vs_mod, '_MAPPING_PATH', str(tmp_path / "nonexistent.json")), \
                 patch.object(vs_mod, '_BM25_PATH', str(tmp_path / "nonexistent.pkl")), \
                 patch.object(vs_mod, '_SYM_INDEX_PATH', str(tmp_path / "nonexistent_sym.bin")), \
                 patch.object(vs_mod, '_SYM_MAPPING_PATH', str(tmp_path / "nonexistent_sym.json")):
                with pytest.raises(FileNotFoundError, match="build_vector_index"):
                    VectorSearch()

    def test_file_not_found_message_contains_script_name(self, tmp_path):
        """FileNotFoundError message mentions the build script."""
        fake_faiss = types.ModuleType("faiss")
        fake_faiss.read_index = MagicMock()
        fake_st = types.ModuleType("sentence_transformers")
        fake_bm25_mod = types.ModuleType("rank_bm25")
        fake_bm25_mod.BM25Okapi = MagicMock()

        # Access the real module (not the shadowed function in quran_ayah_lookup namespace)
        vs_mod = sys.modules["quran_ayah_lookup.vector_search"]

        with patch.dict(
            sys.modules,
            {
                "faiss": fake_faiss,
                "sentence_transformers": fake_st,
                "rank_bm25": fake_bm25_mod,
                "numpy": np,
            },
        ):
            with patch.object(vs_mod, '_INDEX_PATH', str(tmp_path / "x.bin")), \
                 patch.object(vs_mod, '_MAPPING_PATH', str(tmp_path / "x.json")), \
                 patch.object(vs_mod, '_BM25_PATH', str(tmp_path / "x.pkl")), \
                 patch.object(vs_mod, '_SYM_INDEX_PATH', str(tmp_path / "x_sym.bin")), \
                 patch.object(vs_mod, '_SYM_MAPPING_PATH', str(tmp_path / "x_sym.json")):
                try:
                    VectorSearch()
                except FileNotFoundError as exc:
                    assert "scripts/build_vector_index.py" in str(exc)


# ---------------------------------------------------------------------------
# 2. Core search logic (no real faiss needed)
# ---------------------------------------------------------------------------

class TestVectorSearchLogic:

    # --- empty / trivial input ---

    def test_empty_query_returns_empty_match(self):
        vs = _make_vs([{"surah": 1, "ayah": 1}], [0.9], [0])
        result = vs.vector_search("")
        assert result.verses == []
        assert result.similarity == 0.0

    def test_whitespace_query_returns_empty_match(self):
        vs = _make_vs([{"surah": 1, "ayah": 1}], [0.9], [0])
        result = vs.vector_search("   ")
        assert result.verses == []

    def test_empty_index_returns_empty_match(self):
        vs = _make_vs([], [], [])
        vs._index.ntotal = 0
        result = vs.vector_search("الله")
        assert result.verses == []

    # --- threshold filtering ---

    def test_score_below_threshold_returns_empty(self):
        mapping = [{"surah": 1, "ayah": 1}]
        vs = _make_vs(mapping, [0.5], [0])  # score 0.5 < default threshold 0.7
        result = vs.vector_search("الله", threshold=0.7)
        assert result.verses == []
        assert result.similarity == 0.0

    def test_score_above_threshold_returns_match(self):
        verses = [_make_verse(1, 2, "الحمد لله رب العالمين")]
        db = _make_fake_db(verses)
        mapping = [{"surah": 1, "ayah": 2}]
        vs = _make_vs(mapping, [0.85], [0], db=db)
        result = vs.vector_search("الحمد لله", threshold=0.7)
        assert len(result.verses) == 1
        assert result.start_surah == 1
        assert result.start_ayah == 2
        assert result.similarity == pytest.approx(85.0, abs=0.1)

    # --- full vs partial ayah ---

    def test_full_verse_match_has_zero_start_word(self):
        """When a full ayah matches, start_word=0 and end_word=verse_word_count."""
        text = "الحمد لله رب العالمين"
        verses = [_make_verse(1, 2, text)]
        db = _make_fake_db(verses)
        vs = _make_vs([{"surah": 1, "ayah": 2}], [0.9], [0], db=db)
        result = vs.vector_search(text, threshold=0.7)
        assert result.start_word == 0
        assert result.end_word == len(text.split())

    def test_partial_ayah_sets_word_bounds(self):
        """
        A short query against a long verse should produce non-trivial word bounds.
        Ayah al-Kursi (2:255) is long; querying only its first ~10 words
        must yield end_word < total_word_count of the verse.
        """
        full_verse_text = (
            "الله لا اله الا هو الحي القيوم لا تاخذه سنة ولا نوم"
            " له ما في السماوات وما في الارض"
        )
        partial_query = "الله لا اله الا هو الحي القيوم"
        verses = [_make_verse(2, 255, full_verse_text)]
        db = _make_fake_db(verses)
        vs = _make_vs([{"surah": 2, "ayah": 255}], [0.88], [0], db=db)
        result = vs.vector_search(partial_query, threshold=0.7)
        assert result.start_surah == 2
        assert result.start_ayah == 255
        # partial match: end_word must be strictly less than full verse word count
        assert result.end_word < len(full_verse_text.split())

    def test_partial_match_flag_in_matched_text(self):
        """matched_text for a partial ayah should not equal the entire verse text."""
        full_verse_text = (
            "الله لا اله الا هو الحي القيوم لا تاخذه سنة ولا نوم"
            " له ما في السماوات وما في الارض"
        )
        partial_query = "الله لا اله الا هو"
        verses = [_make_verse(2, 255, full_verse_text)]
        db = _make_fake_db(verses)
        vs = _make_vs([{"surah": 2, "ayah": 255}], [0.85], [0], db=db)
        result = vs.vector_search(partial_query, threshold=0.7)
        assert result.matched_text != full_verse_text

    # --- normalize flag ---

    def test_normalize_flag_normalizes_query(self):
        """With normalize=True, query_text in the result should be the normalized form."""
        from quran_ayah_lookup.text_utils import normalize_arabic_text

        diacritized = "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ"
        normalized = normalize_arabic_text(diacritized)
        verses = [_make_verse(1, 1, normalized)]
        db = _make_fake_db(verses)
        vs = _make_vs([{"surah": 1, "ayah": 1}], [0.95], [0], db=db)
        result = vs.vector_search(diacritized, normalize=True, threshold=0.7)
        assert result.query_text == normalized

    def test_no_normalize_uses_raw_query(self):
        """With normalize=False (default), query_text equals the original query."""
        text = "بسم الله الرحمن الرحيم"
        verses = [_make_verse(1, 1, text)]
        db = _make_fake_db(verses)
        vs = _make_vs([{"surah": 1, "ayah": 1}], [0.95], [0], db=db)
        result = vs.vector_search(text, normalize=False, threshold=0.7)
        assert result.query_text == text

    # --- surah_hint expanding window ---

    def test_surah_hint_selects_within_surah(self):
        """With a surah_hint, the match should be restricted to (or near) that surah."""
        verses = [
            _make_verse(55, 1, "الرحمن"),
            _make_verse(2, 255, "الله لا اله الا هو الحي القيوم"),
        ]
        db = _make_fake_db(verses)
        # FAISS returns surah-2 verse as highest score, surah-55 as second
        mapping = [{"surah": 2, "ayah": 255}, {"surah": 55, "ayah": 1}]
        vs = _make_vs(mapping, [0.95, 0.80], [0, 1], db=db)
        result = vs.vector_search("الرحمن", threshold=0.7, surah_hint=55)
        # Despite surah-2 having a higher raw score, the hint steers to surah 55
        assert result.start_surah == 55

    def test_expanding_window_finds_match_outside_hint(self):
        """
        If no match meets threshold within surah_hint, expands to adjacent surahs.
        """
        verses = [
            _make_verse(56, 1, "اذا وقعت الواقعة"),  # surah 56 = hint+1
        ]
        db = _make_fake_db(verses)
        # Only surah 56 in mapping; hint is 55
        mapping = [{"surah": 56, "ayah": 1}]
        vs = _make_vs(mapping, [0.82], [0], db=db)
        result = vs.vector_search("اذا وقعت", threshold=0.7, surah_hint=55)
        # Should expand by 1 and pick surah 56
        assert result.start_surah == 56

    def test_no_match_after_full_expansion_returns_empty(self):
        """If no candidate exceeds threshold after full expansion, return empty."""
        verses = [_make_verse(1, 1, "الحمد لله")]
        db = _make_fake_db(verses)
        mapping = [{"surah": 1, "ayah": 1}]
        vs = _make_vs(mapping, [0.5], [0], db=db)  # score 0.5 < threshold 0.8
        result = vs.vector_search("الرحيم", threshold=0.8, surah_hint=50)
        assert result.verses == []

    # --- gravity / start_after ---

    def test_gravity_boosts_post_position_result(self):
        """
        When start_after is given, a verse appearing after that point should be
        preferred over an otherwise-equal earlier verse.
        """
        verses = [
            _make_verse(2, 100, "verse before anchor"),   # before (3, 1)
            _make_verse(3, 5, "verse after anchor"),       # after  (3, 1)
        ]
        db = _make_fake_db(verses)
        # Both have identical raw scores; gravity should push surah-3 ahead
        mapping = [{"surah": 2, "ayah": 100}, {"surah": 3, "ayah": 5}]
        vs = _make_vs(mapping, [0.80, 0.80], [0, 1], db=db)
        result = vs.vector_search("test", threshold=0.7, start_after=(3, 1))
        assert result.start_surah == 3

    def test_gravity_does_not_affect_reported_similarity(self):
        """The reported similarity is the raw cosine score, not the boosted one."""
        verses = [_make_verse(3, 5, "verse after anchor")]
        db = _make_fake_db(verses)
        mapping = [{"surah": 3, "ayah": 5}]
        raw_score = 0.80
        vs = _make_vs(mapping, [raw_score], [0], db=db)
        result = vs.vector_search("test", threshold=0.7, start_after=(2, 1))
        # Reported similarity should equal raw_score * 100, not boosted value
        assert result.similarity == pytest.approx(raw_score * 100, abs=0.1)

    # --- sequence detection (multi-verse queries) ---

    def test_sequence_detection_returns_multiple_verses(self):
        """
        A query significantly longer than one verse should include extra verses.
        """
        v1 = _make_verse(55, 1, "الرحمن")
        v2 = _make_verse(55, 2, "علم القران")
        v3 = _make_verse(55, 3, "خلق الانسان")
        db = _make_fake_db([v1, v2, v3])
        mapping = [
            {"surah": 55, "ayah": 1},
            {"surah": 55, "ayah": 2},
            {"surah": 55, "ayah": 3},
        ]
        # Long query to trigger sequence detection (>1.3x v1 word count)
        long_query = "الرحمن علم القران خلق الانسان علمه البيان"
        vs = _make_vs(mapping, [0.90, 0.70, 0.65], [0, 1, 2], db=db)
        result = vs.vector_search(long_query, threshold=0.7)
        assert len(result.verses) > 1
        assert result.verses[0].surah_number == 55
        assert result.verses[0].ayah_number == 1

    def test_sequence_detection_caps_at_3_extra_verses(self):
        """Extra verses added during sequence detection are capped at 3."""
        v1 = _make_verse(2, 1, "الم")
        extra = [_make_verse(2, i, f"verse {i}") for i in range(2, 10)]
        db = _make_fake_db([v1] + extra)
        mapping = [{"surah": 2, "ayah": i} for i in range(1, 10)]
        scores = [0.90] + [0.5] * 8
        ids = list(range(9))
        # Very long query to maximise sequence detection
        very_long_query = " ".join(["test"] * 50)
        vs = _make_vs(mapping, scores, ids, db=db)
        result = vs.vector_search(very_long_query, threshold=0.7)
        # At most 1 (best) + 3 (extra) = 4 verses
        assert len(result.verses) <= 4

    # --- MultiAyahMatch fields ---

    def test_result_similarity_is_scaled_to_100(self):
        verses = [_make_verse(1, 1, "بسم الله الرحمن الرحيم")]
        db = _make_fake_db(verses)
        vs = _make_vs([{"surah": 1, "ayah": 1}], [0.93], [0], db=db)
        result = vs.vector_search("بسم الله", threshold=0.7)
        assert result.similarity == pytest.approx(93.0, abs=0.1)

    def test_result_reference_format(self):
        verses = [_make_verse(55, 1, "الرحمن")]
        db = _make_fake_db(verses)
        vs = _make_vs([{"surah": 55, "ayah": 1}], [0.90], [0], db=db)
        result = vs.vector_search("الرحمن", threshold=0.7)
        assert result.get_reference() == "55:1"

    def test_invalid_faiss_id_is_skipped(self):
        """FAISS may return -1 padding ids; these should be safely ignored."""
        verses = [_make_verse(1, 1, "بسم الله الرحمن الرحيم")]
        db = _make_fake_db(verses)
        # id=-1 is invalid; id=0 is valid
        vs = _make_vs([{"surah": 1, "ayah": 1}], [0.9, 0.85], [-1, 0], db=db)
        result = vs.vector_search("بسم الله", threshold=0.7)
        assert len(result.verses) == 1


# ---------------------------------------------------------------------------
# 3. _select_best helper
# ---------------------------------------------------------------------------

class TestSelectBest:

    def _vs(self):
        """Minimal VectorSearch for testing _select_best."""
        vs: VectorSearch = object.__new__(VectorSearch)
        vs._mapping = []
        return vs

    def test_no_hint_returns_highest_score(self):
        vs = self._vs()
        candidates = [(0.9, 1, 1), (0.8, 2, 1), (0.7, 3, 1)]
        faiss_score_map = {(1, 1): 0.9, (2, 1): 0.8, (3, 1): 0.7}
        result = vs._select_best(candidates, threshold=0.7, surah_hint=None, faiss_score_map=faiss_score_map)
        assert result == (0.9, 1, 1)

    def test_no_hint_below_threshold_returns_none(self):
        vs = self._vs()
        candidates = [(0.5, 1, 1)]
        faiss_score_map = {(1, 1): 0.5}
        result = vs._select_best(candidates, threshold=0.7, surah_hint=None, faiss_score_map=faiss_score_map)
        assert result is None

    def test_empty_candidates_returns_none(self):
        vs = self._vs()
        result = vs._select_best([], threshold=0.7, surah_hint=None, faiss_score_map={})
        assert result is None

    def test_hint_prefers_matching_surah(self):
        vs = self._vs()
        candidates = [(0.90, 2, 255), (0.85, 55, 1)]  # surah 2 has higher RRF score
        faiss_score_map = {(2, 255): 0.90, (55, 1): 0.85}
        result = vs._select_best(candidates, threshold=0.7, surah_hint=55, faiss_score_map=faiss_score_map)
        # surah 55 should be chosen despite lower RRF score
        assert result[1] == 55

    def test_hint_expands_to_adjacent_surah(self):
        vs = self._vs()
        # Only surah 56 available; hint is 55
        candidates = [(0.80, 56, 1)]
        faiss_score_map = {(56, 1): 0.80}
        result = vs._select_best(candidates, threshold=0.7, surah_hint=55, faiss_score_map=faiss_score_map)
        assert result is not None
        assert result[1] == 56

    def test_hint_clamps_window_at_boundaries(self):
        """Window should not go below surah 1 or above surah 114."""
        vs = self._vs()
        candidates = [(0.80, 1, 1)]
        faiss_score_map = {(1, 1): 0.80}
        result = vs._select_best(candidates, threshold=0.7, surah_hint=1, faiss_score_map=faiss_score_map)
        assert result is not None

    def test_hint_full_expansion_returns_none_if_still_below_threshold(self):
        vs = self._vs()
        candidates = [(0.50, 50, 1)]  # below threshold 0.8
        faiss_score_map = {(50, 1): 0.50}
        result = vs._select_best(candidates, threshold=0.8, surah_hint=50, faiss_score_map=faiss_score_map)
        assert result is None


# ---------------------------------------------------------------------------
# 4. _is_after helper
# ---------------------------------------------------------------------------

class TestIsAfter:

    def test_same_surah_later_ayah_is_after(self):
        assert VectorSearch._is_after(2, 256, (2, 255)) is True

    def test_same_surah_earlier_ayah_is_not_after(self):
        assert VectorSearch._is_after(2, 254, (2, 255)) is False

    def test_same_position_is_not_after(self):
        assert VectorSearch._is_after(2, 255, (2, 255)) is False

    def test_later_surah_is_after(self):
        assert VectorSearch._is_after(3, 1, (2, 255)) is True

    def test_earlier_surah_is_not_after(self):
        assert VectorSearch._is_after(1, 7, (2, 1)) is False


# ---------------------------------------------------------------------------
# 5. _get_next_verses helper
# ---------------------------------------------------------------------------

class TestGetNextVerses:

    def test_returns_correct_next_verse(self):
        v1 = _make_verse(1, 1, "بسم الله الرحمن الرحيم")
        v2 = _make_verse(1, 2, "الحمد لله رب العالمين")
        db = _make_fake_db([v1, v2])
        vs: VectorSearch = object.__new__(VectorSearch)
        vs._db = db
        result = vs._get_next_verses(1, 1, count=1)
        assert len(result) == 1
        assert result[0].ayah_number == 2

    def test_caps_at_requested_count(self):
        verses = [_make_verse(1, i, f"verse {i}") for i in range(1, 8)]
        db = _make_fake_db(verses)
        vs: VectorSearch = object.__new__(VectorSearch)
        vs._db = db
        result = vs._get_next_verses(1, 1, count=3)
        assert len(result) == 3

    def test_missing_starting_verse_returns_empty(self):
        verses = [_make_verse(1, 1, "verse")]
        db = _make_fake_db(verses)
        vs: VectorSearch = object.__new__(VectorSearch)
        vs._db = db
        result = vs._get_next_verses(99, 99, count=2)
        assert result == []


# ---------------------------------------------------------------------------
# 6. CLI integration
# ---------------------------------------------------------------------------

class TestCLI:

    def test_vector_search_command_success(self):
        from click.testing import CliRunner
        from quran_ayah_lookup.cli import cli

        verse = _make_verse(2, 255, "الله لا اله الا هو الحي القيوم")
        match = MultiAyahMatch(
            verses=[verse],
            similarity=88.0,
            matched_text="الله لا اله الا هو",
            query_text="الله لا اله الا هو",
            start_surah=2,
            start_ayah=255,
            start_word=0,
            end_word=6,
            end_surah=2,
            end_ayah=255,
        )

        with patch("quran_ayah_lookup.cli._VECTOR_AVAILABLE", True), \
             patch("quran_ayah_lookup.cli.VectorSearch") as MockVS:
            mock_instance = MockVS.return_value
            mock_instance.vector_search.return_value = match

            runner = CliRunner()
            result = runner.invoke(
                cli, ["vector-search", "الله لا اله الا هو"], catch_exceptions=False
            )
            assert result.exit_code == 0
            assert "2:255" in result.output

    def test_vector_search_command_not_available(self):
        from click.testing import CliRunner
        from quran_ayah_lookup.cli import cli

        with patch("quran_ayah_lookup.cli._VECTOR_AVAILABLE", False):
            runner = CliRunner()
            result = runner.invoke(cli, ["vector-search", "test"])
            assert result.exit_code != 0
            assert "quran-ayah-lookup[vector]" in result.output

    def test_vector_search_command_no_match(self):
        from click.testing import CliRunner
        from quran_ayah_lookup.cli import cli

        empty_match = VectorSearch._empty_match("no match")

        with patch("quran_ayah_lookup.cli._VECTOR_AVAILABLE", True), \
             patch("quran_ayah_lookup.cli.VectorSearch") as MockVS:
            MockVS.return_value.vector_search.return_value = empty_match
            runner = CliRunner()
            result = runner.invoke(cli, ["vector-search", "no match"])
            assert result.exit_code == 0
            assert "No match found" in result.output

    def test_vector_search_command_invalid_start_after(self):
        from click.testing import CliRunner
        from quran_ayah_lookup.cli import cli

        with patch("quran_ayah_lookup.cli._VECTOR_AVAILABLE", True):
            runner = CliRunner()
            result = runner.invoke(
                cli, ["vector-search", "test", "--start-after", "bad-format"]
            )
            assert result.exit_code != 0
            assert "surah:ayah" in result.output

    def test_vector_search_command_invalid_threshold(self):
        from click.testing import CliRunner
        from quran_ayah_lookup.cli import cli

        with patch("quran_ayah_lookup.cli._VECTOR_AVAILABLE", True), \
             patch("quran_ayah_lookup.cli.VectorSearch"):
            runner = CliRunner()
            result = runner.invoke(
                cli, ["vector-search", "test", "--threshold", "1.5"]
            )
            assert result.exit_code != 0
            assert "Threshold" in result.output

    def test_vector_search_command_file_not_found(self):
        from click.testing import CliRunner
        from quran_ayah_lookup.cli import cli

        with patch("quran_ayah_lookup.cli._VECTOR_AVAILABLE", True), \
             patch("quran_ayah_lookup.cli.VectorSearch") as MockVS:
            MockVS.side_effect = FileNotFoundError("index not built")
            runner = CliRunner()
            result = runner.invoke(cli, ["vector-search", "test"])
            assert result.exit_code != 0


# ---------------------------------------------------------------------------
# 7. API integration
# ---------------------------------------------------------------------------

class TestAPI:

    @pytest.fixture
    def client(self):
        """Return a FastAPI TestClient. Skips if FastAPI not installed."""
        pytest.importorskip("fastapi")
        pytest.importorskip("httpx")
        from fastapi.testclient import TestClient
        from quran_ayah_lookup.api import app
        return TestClient(app)

    def test_vector_search_endpoint_success(self, client):
        verse = _make_verse(2, 255, "الله لا اله الا هو الحي القيوم")
        match = MultiAyahMatch(
            verses=[verse],
            similarity=88.5,
            matched_text="الله لا اله الا هو",
            query_text="الله لا اله الا هو",
            start_surah=2,
            start_ayah=255,
            start_word=0,
            end_word=6,
            end_surah=2,
            end_ayah=255,
        )

        with patch("quran_ayah_lookup.api._VECTOR_AVAILABLE", True), \
             patch("quran_ayah_lookup.api._get_vs") as mock_get_vs:
            mock_get_vs.return_value.vector_search.return_value = match
            response = client.get("/vector-search?query=الله لا اله الا هو")
        assert response.status_code == 200
        data = response.json()
        assert data["start_surah"] == 2
        assert data["start_ayah"] == 255
        assert data["start_word"] == 0
        assert data["end_word"] == 6
        assert data["similarity"] == pytest.approx(88.5, abs=0.1)

    def test_vector_search_endpoint_503_when_unavailable(self, client):
        with patch("quran_ayah_lookup.api._VECTOR_AVAILABLE", False):
            response = client.get("/vector-search?query=test")
        assert response.status_code == 503
        assert "quran-ayah-lookup[vector]" in response.json()["detail"]

    def test_vector_search_endpoint_503_on_file_not_found(self, client):
        with patch("quran_ayah_lookup.api._VECTOR_AVAILABLE", True), \
             patch("quran_ayah_lookup.api._get_vs") as mock_get_vs:
            mock_get_vs.side_effect = FileNotFoundError("index not built")
            response = client.get("/vector-search?query=test")
        assert response.status_code == 503

    def test_vector_search_endpoint_400_on_unpaired_start_after(self, client):
        """Providing only start_after_surah without start_after_ayah is invalid."""
        with patch("quran_ayah_lookup.api._VECTOR_AVAILABLE", True):
            response = client.get(
                "/vector-search?query=test&start_after_surah=2"
            )
        assert response.status_code == 400

    def test_vector_search_endpoint_with_surah_hint(self, client):
        verse = _make_verse(55, 1, "الرحمن")
        match = MultiAyahMatch(
            verses=[verse],
            similarity=92.0,
            matched_text="الرحمن",
            query_text="الرحمن",
            start_surah=55,
            start_ayah=1,
            start_word=0,
            end_word=1,
            end_surah=55,
            end_ayah=1,
        )
        with patch("quran_ayah_lookup.api._VECTOR_AVAILABLE", True), \
             patch("quran_ayah_lookup.api._get_vs") as mock_get_vs:
            mock_get_vs.return_value.vector_search.return_value = match
            response = client.get("/vector-search?query=الرحمن&surah_hint=55")
        assert response.status_code == 200
        assert response.json()["start_surah"] == 55

    def test_vector_search_appears_in_root_endpoints(self, client):
        """The root endpoint's endpoint map should include /vector-search."""
        response = client.get("/")
        assert response.status_code == 200
        assert "/vector-search" in response.json()["endpoints"].values()


# ---------------------------------------------------------------------------
# 8. Build script smoke test
# ---------------------------------------------------------------------------

class TestBuildScript:

    def test_build_script_creates_output_files(self, tmp_path):
        """
        Smoke-test the indexing script: mock all heavy deps and verify that
        faiss.write_index is called twice (asymmetric + symmetric) and
        pickle.dump is called once (BM25).
        """
        # Locate the script
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        script_path = os.path.join(repo_root, "scripts", "build_vector_index.py")
        assert os.path.isfile(script_path), "Build script not found"

        expected_index = os.path.join(
            repo_root, "src", "quran_ayah_lookup", "resources", "vector", "faiss_index.bin"
        )
        expected_sym_index = os.path.join(
            repo_root, "src", "quran_ayah_lookup", "resources", "vector", "faiss_sym_index.bin"
        )

        # Build minimal stub replacements for optional deps
        fake_index = MagicMock()

        fake_faiss = types.ModuleType("faiss")
        fake_faiss.IndexFlatIP = MagicMock(return_value=fake_index)
        fake_faiss.write_index = MagicMock()
        fake_faiss.read_index = MagicMock()

        # Asymmetric model (e5-base) → 768-dim
        fake_model_asym = MagicMock()
        fake_model_asym.encode = MagicMock(
            return_value=np.ones((3, 768), dtype=np.float32)
        )
        # Symmetric model (MiniLM) → 384-dim
        fake_model_sym = MagicMock()
        fake_model_sym.encode = MagicMock(
            return_value=np.ones((3, 384), dtype=np.float32)
        )

        call_count = [0]
        def _make_model(model_name):
            call_count[0] += 1
            return fake_model_asym if call_count[0] == 1 else fake_model_sym

        fake_st = types.ModuleType("sentence_transformers")
        fake_st.SentenceTransformer = MagicMock(side_effect=_make_model)

        fake_bm25_instance = MagicMock()
        fake_bm25_mod = types.ModuleType("rank_bm25")
        fake_bm25_mod.BM25Okapi = MagicMock(return_value=fake_bm25_instance)

        fake_verses = [
            _make_verse(1, 1, "بسم الله الرحمن الرحيم"),
            _make_verse(1, 2, "الحمد لله رب العالمين"),
            _make_verse(2, 1, "الم"),
        ]
        mock_db = MagicMock()
        mock_db.get_all_verses.return_value = fake_verses

        import importlib.util
        spec = importlib.util.spec_from_file_location("build_vector_index", script_path)
        mod = importlib.util.module_from_spec(spec)

        with patch.dict(
            sys.modules,
            {
                "faiss": fake_faiss,
                "sentence_transformers": fake_st,
                "rank_bm25": fake_bm25_mod,
                "numpy": np,
            },
        ), patch("sys.argv", ["build_vector_index.py"]), \
           patch("builtins.open", mock_open()), \
           patch("os.makedirs"), \
           patch("pickle.dump") as mock_pickle_dump, \
           patch("quran_ayah_lookup.loader.get_quran_database", return_value=mock_db):
            spec.loader.exec_module(mod)
            mod.main()

        # write_index called twice: asymmetric + symmetric
        assert fake_faiss.write_index.call_count == 2
        paths_written = [
            fake_faiss.write_index.call_args_list[0][0][1],
            fake_faiss.write_index.call_args_list[1][0][1],
        ]
        assert expected_index in paths_written
        assert expected_sym_index in paths_written

        # BM25 pickled once
        mock_pickle_dump.assert_called_once()
        assert mock_pickle_dump.call_args[0][0] is fake_bm25_instance

    def test_build_script_missing_deps_exits_with_code_1(self, tmp_path):
        """When faiss is missing, the script should exit with code 1."""
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        script_path = os.path.join(repo_root, "scripts", "build_vector_index.py")

        import importlib.util
        spec = importlib.util.spec_from_file_location("build_vector_index_nodeps", script_path)
        mod = importlib.util.module_from_spec(spec)

        with patch.dict(sys.modules, {"faiss": None}), \
             patch("sys.argv", ["build_vector_index.py"]):
            spec.loader.exec_module(mod)
            with pytest.raises(SystemExit) as exc_info:
                mod.main()
            assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# 9. Hybrid search — RRF, BM25, and e5 model specifics
# ---------------------------------------------------------------------------

class TestHybridSearch:

    def test_rrf_fuse_basic(self):
        """RRF correctly combines two ranked lists and scores all documents."""
        faiss_ranked = [(1, 1), (1, 2), (1, 3)]
        bm25_ranked  = [(1, 2), (1, 1), (1, 3)]
        result = VectorSearch._rrf_fuse(faiss_ranked, bm25_ranked)
        scores = {(s, a): sc for sc, s, a in result}

        # (1,1): rank1 in faiss + rank2 in bm25 = 1/61 + 1/62
        # (1,2): rank2 in faiss + rank1 in bm25 = 1/62 + 1/61  (same)
        # (1,3): rank3 in faiss + rank3 in bm25 = 1/63 + 1/63  (lower)
        assert (1, 1) in scores
        assert (1, 2) in scores
        assert (1, 3) in scores
        assert scores[(1, 1)] > scores[(1, 3)]
        assert scores[(1, 2)] > scores[(1, 3)]
        assert scores[(1, 1)] == pytest.approx(scores[(1, 2)], abs=1e-9)

    def test_rrf_fuse_single_system(self):
        """RRF with a single ranked list degrades gracefully (no errors)."""
        faiss_ranked = [(1, 1), (1, 2)]
        result = VectorSearch._rrf_fuse(faiss_ranked)
        assert len(result) == 2
        # Higher-ranked (1,1) should score better
        assert result[0][0] > result[1][0]
        assert result[0][1:] == (1, 1)

    def test_rrf_kw_exact_match_boosts_rank(self):
        """BM25 exact keyword match lifts a lower-FAISS-ranked verse via RRF."""
        # FAISS prefers (1,1); BM25 sees keyword only in (2,1)
        faiss_ranked = [(1, 1), (2, 1)]
        bm25_ranked  = [(2, 1)]  # (1,1) has no keyword overlap (score=0, excluded)
        result = VectorSearch._rrf_fuse(faiss_ranked, bm25_ranked)
        scores = {(s, a): sc for sc, s, a in result}
        # (2,1): 1/62 (faiss rank 2) + 1/61 (bm25 rank 1) = 0.03252
        # (1,1): 1/61 (faiss rank 1) only               = 0.01639
        assert scores[(2, 1)] > scores[(1, 1)]

    def test_bm25_zero_score_excluded_from_ranked_list(self):
        """_bm25_search excludes verses with zero BM25 score to avoid noise."""
        mapping = [
            {"surah": 1, "ayah": 1},
            {"surah": 1, "ayah": 2},
            {"surah": 2, "ayah": 1},
        ]
        # Only index 1 has a positive BM25 score
        bm25_scores = np.array([0.0, 1.5, 0.0])
        vs = _make_vs(mapping, [0.9, 0.8, 0.7], [0, 1, 2], bm25_scores=bm25_scores)
        result = vs._bm25_search("الحمد لله")
        assert len(result) == 1
        assert result[0] == (1, 2)

    def test_encode_query_prefix(self):
        """_encode_query prepends 'query: ' before passing text to the model."""
        vs: VectorSearch = object.__new__(VectorSearch)
        mock_model = MagicMock()
        mock_model.encode.return_value = np.ones((1, 768), dtype=np.float32)
        vs._model = mock_model
        vs._encode_query("الله اكبر")
        call_args = mock_model.encode.call_args[0][0]  # first positional arg (list)
        assert call_args == ["query: الله اكبر"]

    def test_model_name_is_e5(self):
        """The asymmetric module uses intfloat/multilingual-e5-base."""
        from quran_ayah_lookup.vector_search import _MODEL_NAME
        assert _MODEL_NAME == "intfloat/multilingual-e5-base"

    def test_sym_model_name_is_minilm(self):
        """The symmetric model is paraphrase-multilingual-MiniLM-L12-v2."""
        assert _SYM_MODEL_NAME == "paraphrase-multilingual-MiniLM-L12-v2"

    def test_symmetric_mode_returns_match(self):
        """asymmetric=False uses the symmetric MiniLM index and returns a match."""
        verses = [_make_verse(1, 2, "الحمد لله رب العالمين")]
        db = _make_fake_db(verses)
        mapping = [{"surah": 1, "ayah": 2}]
        vs = _make_vs(mapping, [0.85], [0], db=db)
        result = vs.vector_search("الحمد لله", threshold=0.7, asymmetric=False)
        assert len(result.verses) == 1
        assert result.start_surah == 1
        assert result.start_ayah == 2
        assert result.similarity == pytest.approx(85.0, abs=0.1)

    def test_symmetric_mode_uses_sym_index(self):
        """With asymmetric=False, _sym_index.search is called, not _index.search."""
        mapping = [{"surah": 1, "ayah": 1}]
        vs = _make_vs(mapping, [0.9], [0])
        vs.vector_search("test", threshold=0.7, asymmetric=False)
        vs._sym_index.search.assert_called_once()
        vs._index.search.assert_not_called()

    def test_asymmetric_mode_uses_asym_index(self):
        """With asymmetric=True (default), _index.search is called, not _sym_index."""
        mapping = [{"surah": 1, "ayah": 1}]
        vs = _make_vs(mapping, [0.9], [0])
        vs.vector_search("test", threshold=0.7, asymmetric=True)
        vs._index.search.assert_called_once()
        vs._sym_index.search.assert_not_called()

    def test_semantic_only_skips_bm25(self):
        """With semantic_only=True, BM25 get_scores is never called."""
        mapping = [{"surah": 1, "ayah": 1}]
        vs = _make_vs(mapping, [0.9], [0])
        vs.vector_search("test", threshold=0.7, asymmetric=True, semantic_only=True)
        vs._bm25.get_scores.assert_not_called()

    def test_semantic_only_false_calls_bm25(self):
        """With semantic_only=False (default), BM25 get_scores is called."""
        mapping = [{"surah": 1, "ayah": 1}]
        vs = _make_vs(mapping, [0.9], [0])
        vs.vector_search("test", threshold=0.7, asymmetric=True, semantic_only=False)
        vs._bm25.get_scores.assert_called_once()

    def test_semantic_only_still_returns_match(self):
        """semantic_only=True still returns a valid match using FAISS scores."""
        verses = [_make_verse(2, 255, "الله لا اله الا هو الحي القيوم")]
        db = _make_fake_db(verses)
        mapping = [{"surah": 2, "ayah": 255}]
        vs = _make_vs(mapping, [0.88], [0], db=db)
        result = vs.vector_search("الله لا اله", threshold=0.7, asymmetric=True, semantic_only=True)
        assert result.start_surah == 2
        assert result.start_ayah == 255
        assert result.similarity == pytest.approx(88.0, abs=0.1)

    def test_semantic_only_with_symmetric_mode_has_no_effect(self):
        """semantic_only has no effect with asymmetric=False (symmetric is already FAISS-only)."""
        verses = [_make_verse(1, 2, "الحمد لله رب العالمين")]
        db = _make_fake_db(verses)
        mapping = [{"surah": 1, "ayah": 2}]
        vs = _make_vs(mapping, [0.85], [0], db=db)
        # Both should return the same result, and neither calls BM25
        result_a = vs.vector_search("الحمد لله", threshold=0.7, asymmetric=False, semantic_only=False)
        result_b = vs.vector_search("الحمد لله", threshold=0.7, asymmetric=False, semantic_only=True)
        assert result_a.start_surah == result_b.start_surah
        assert result_a.start_ayah == result_b.start_ayah
        vs._bm25.get_scores.assert_not_called()
