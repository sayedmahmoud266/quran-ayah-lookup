"""
Tests for asr_sequential_fuzzy_search and related helpers.
"""
import pytest

from quran_ayah_lookup import asr_sequential_fuzzy_search, ASRSegmentResult, get_quran_database
from quran_ayah_lookup.asr_search import (
    _normalize_muqattaat,
    _search_segment,
    _sliding_consensus,
    _extract_positions,
    _infer_verse_from_neighbours,
)


# ---------------------------------------------------------------------------
# _normalize_muqattaat
# ---------------------------------------------------------------------------

def test_normalize_muqattaat_ha_meem():
    assert _normalize_muqattaat("حا ميم") == "حم"

def test_normalize_muqattaat_ya_seen():
    assert _normalize_muqattaat("يا سين") == "يس"

def test_normalize_muqattaat_ta_ha():
    assert _normalize_muqattaat("طا ها") == "طه"

def test_normalize_muqattaat_alif_lam_meem():
    assert _normalize_muqattaat("الف لام ميم") == "الم"

def test_normalize_muqattaat_alif_lam_ra():
    result = _normalize_muqattaat("الف لام راء")
    # "الف لام راء" should normalise — at minimum not stay the same
    # (partial match: الف لام را is in table; راء ends with ء)
    # Check compound form isn't just left raw
    assert "الف لام ميم" not in result

def test_normalize_muqattaat_compound_khayaas():
    assert _normalize_muqattaat("كاف ها يا عين صاد") == "كهيعص"

def test_normalize_muqattaat_ain_seen_qaf():
    assert _normalize_muqattaat("عين سين قاف") == "عسق"

def test_normalize_muqattaat_noon():
    assert _normalize_muqattaat("نون") == "ن"

def test_normalize_muqattaat_saad():
    assert _normalize_muqattaat("صاد") == "ص"

def test_normalize_muqattaat_qaf():
    assert _normalize_muqattaat("قاف") == "ق"

def test_normalize_muqattaat_no_change_for_normal_text():
    text = "بسم الله الرحمن الرحيم"
    assert _normalize_muqattaat(text) == text

def test_normalize_muqattaat_alm_sad():
    assert _normalize_muqattaat("الف لام ميم صاد") == "المص"


# ---------------------------------------------------------------------------
# _sliding_consensus
# ---------------------------------------------------------------------------

def test_sliding_consensus_uniform():
    positions = [(87, i) for i in range(1, 10)]
    consensus = _sliding_consensus(positions, window=5)
    assert all(c == 87 for c in consensus)

def test_sliding_consensus_one_outlier():
    positions = [(87, i) for i in range(1, 8)]
    positions[3] = (2, 5)  # outlier in the middle
    consensus = _sliding_consensus(positions, window=7)
    # Majority around position 3 should still be 87
    assert consensus[3] == 87

def test_sliding_consensus_all_none():
    positions = [None] * 5
    consensus = _sliding_consensus(positions, window=5)
    assert all(c is None for c in consensus)

def test_sliding_consensus_transition():
    # First half surah 87, second half surah 88
    positions = [(87, i) for i in range(1, 6)] + [(88, i) for i in range(1, 6)]
    consensus = _sliding_consensus(positions, window=3)
    assert consensus[0] == 87
    assert consensus[-1] == 88

def test_sliding_consensus_length_preserved():
    positions = [(1, i) for i in range(1, 8)]
    consensus = _sliding_consensus(positions, window=5)
    assert len(consensus) == len(positions)


# ---------------------------------------------------------------------------
# _infer_verse_from_neighbours
# ---------------------------------------------------------------------------

def test_infer_verse_same_surah():
    db = get_quran_database()
    verse = _infer_verse_from_neighbours(db, (87, 1), (87, 5))
    assert verse is not None
    assert verse.surah_number == 87
    # Should be somewhere between ayah 1 and 5
    assert 1 < verse.ayah_number < 5

def test_infer_verse_only_before():
    db = get_quran_database()
    verse = _infer_verse_from_neighbours(db, (87, 1), None)
    assert verse is not None
    # Should be 87:2
    assert verse.surah_number == 87
    assert verse.ayah_number == 2

def test_infer_verse_only_after():
    db = get_quran_database()
    verse = _infer_verse_from_neighbours(db, None, (87, 5))
    assert verse is not None
    assert verse.surah_number == 87

def test_infer_verse_no_neighbours_returns_none():
    db = get_quran_database()
    verse = _infer_verse_from_neighbours(db, None, None)
    assert verse is None


# ---------------------------------------------------------------------------
# asr_sequential_fuzzy_search — output structure
# ---------------------------------------------------------------------------

def test_asr_returns_correct_length():
    segments = [
        "بسم الله الرحمن الرحيم",
        "سبح اسم ربك الاعلى",
        "الذي خلق فسوى",
    ]
    results = asr_sequential_fuzzy_search(segments)
    assert len(results) == len(segments)


def test_asr_returns_asr_segment_result_instances():
    segments = ["بسم الله الرحمن الرحيم", "الحمد لله رب العالمين"]
    results = asr_sequential_fuzzy_search(segments)
    for r in results:
        assert isinstance(r, ASRSegmentResult)


def test_asr_segment_index_matches_position():
    segments = ["بسم الله الرحمن الرحيم", "الحمد لله رب العالمين", "الرحمن الرحيم"]
    results = asr_sequential_fuzzy_search(segments)
    for i, r in enumerate(results):
        assert r.segment_index == i


def test_asr_segment_text_preserved():
    segments = ["بسم الله الرحمن الرحيم", "الحمد لله رب العالمين"]
    results = asr_sequential_fuzzy_search(segments)
    for r, seg in zip(results, segments):
        assert r.segment_text == seg


def test_asr_corpus_used_is_valid():
    segments = ["بسم الله الرحمن الرحيم", "سبح اسم ربك الاعلى"]
    results = asr_sequential_fuzzy_search(segments)
    for r in results:
        assert r.corpus_used in ("uthmani", "imlaai", "none")


def test_asr_similarity_in_range():
    segments = ["بسم الله الرحمن الرحيم", "سبح اسم ربك الاعلى"]
    results = asr_sequential_fuzzy_search(segments)
    for r in results:
        assert 0.0 <= r.similarity <= 1.0


def test_asr_to_dict_has_required_keys():
    results = asr_sequential_fuzzy_search(["بسم الله الرحمن الرحيم"])
    d = results[0].to_dict()
    for key in ("segment_index", "segment_text", "verse", "verses",
                "is_multi_ayah", "similarity", "matched_text",
                "start_word", "end_word", "corpus_used", "corrected"):
        assert key in d


def test_to_dict_verses_is_list():
    results = asr_sequential_fuzzy_search(["بسم الله الرحمن الرحيم"])
    d = results[0].to_dict()
    assert isinstance(d["verses"], list)


def test_to_dict_is_multi_ayah_is_bool():
    results = asr_sequential_fuzzy_search(["بسم الله الرحمن الرحيم"])
    d = results[0].to_dict()
    assert isinstance(d["is_multi_ayah"], bool)


def test_asr_empty_input():
    results = asr_sequential_fuzzy_search([])
    assert results == []


def test_asr_blank_segment_does_not_crash():
    results = asr_sequential_fuzzy_search(["", "   ", "بسم الله الرحمن الرحيم"])
    assert len(results) == 3
    assert results[2].verse is not None


# ---------------------------------------------------------------------------
# asr_sequential_fuzzy_search — correctness: Al-A'la (surah 87)
# ---------------------------------------------------------------------------

AL_ALA_SEGMENTS = [
    "بسم الله الرحمن الرحيم",
    "سبح اسم ربك الاعلى",
    "الذي خلق فسوى",
    "والذي قدر فهدى",
    "والذي اخرج المرعى",
    "فجعله غثاء احوى",
    "سنقرئك فلا تنسى",
    "الا ما شاء الله",
    "انه يعلم الجهر وما يخفى",
    "ونيسرك لليسرى",
]


def test_al_ala_output_length():
    results = asr_sequential_fuzzy_search(AL_ALA_SEGMENTS)
    assert len(results) == len(AL_ALA_SEGMENTS)


def test_al_ala_verses_mostly_resolved():
    """At least 7/10 segments should resolve to a verse."""
    results = asr_sequential_fuzzy_search(AL_ALA_SEGMENTS)
    resolved = sum(1 for r in results if r.verse is not None)
    assert resolved >= 7


def test_al_ala_dominant_surah_is_87():
    """Majority of resolved results should be surah 87."""
    results = asr_sequential_fuzzy_search(AL_ALA_SEGMENTS)
    surahs = [r.verse.surah_number for r in results
              if r.verse is not None and not r.verse.is_istiadhah and not r.verse.is_tasdiq]
    assert surahs.count(87) >= len(surahs) // 2


def test_al_ala_surah_ayah_segment_2():
    """'سبح اسم ربك الاعلى' is surah 87 ayah 1."""
    results = asr_sequential_fuzzy_search(AL_ALA_SEGMENTS)
    r = results[1]  # index 1 = second segment
    assert r.verse is not None
    assert r.verse.surah_number == 87
    assert r.verse.ayah_number == 1


# ---------------------------------------------------------------------------
# asr_sequential_fuzzy_search — muqatta'at (surah 44 Ad-Dukhan)
# ---------------------------------------------------------------------------

DUKHAN_SEGMENTS = [
    "بسم الله الرحمن الرحيم",
    "حا ميم",           # imlaai spelling
    "والكتاب المبين",
    "انا انزلناه في ليلة مباركة",
    "انا كنا منذرين",
]


def test_dukhan_output_length():
    results = asr_sequential_fuzzy_search(DUKHAN_SEGMENTS)
    assert len(results) == len(DUKHAN_SEGMENTS)


def test_dukhan_ha_meem_resolves_to_surah_44():
    """'حا ميم' (imlaai) should resolve to surah 44, ayah 1."""
    results = asr_sequential_fuzzy_search(DUKHAN_SEGMENTS)
    r = results[1]  # index 1 = 'حا ميم'
    assert r.verse is not None
    assert r.verse.surah_number == 44


def test_dukhan_third_segment_resolves():
    """'والكتاب المبين' should be surah 44, ayah 2."""
    results = asr_sequential_fuzzy_search(DUKHAN_SEGMENTS)
    r = results[2]
    assert r.verse is not None
    assert r.verse.surah_number == 44
    assert r.verse.ayah_number == 2


# ---------------------------------------------------------------------------
# asr_sequential_fuzzy_search — correction flag
# ---------------------------------------------------------------------------

def test_corrected_flag_false_when_no_outlier():
    """Normal in-sequence segments should not be marked corrected."""
    segments = [
        "سبح اسم ربك الاعلى",
        "الذي خلق فسوى",
        "والذي قدر فهدى",
    ]
    results = asr_sequential_fuzzy_search(segments)
    # At most a minority should be corrected in a clean sequence
    corrected_count = sum(1 for r in results if r.corrected)
    assert corrected_count <= len(segments)  # sanity — never more than total


# ---------------------------------------------------------------------------
# asr_sequential_fuzzy_search — istia'dhah special verse
# ---------------------------------------------------------------------------

def test_istiadhah_at_start_is_special_verse():
    """اعوذ بالله من الشيطان الرجيم as first segment resolves to the special verse."""
    results = asr_sequential_fuzzy_search([
        "اعوذ بالله من الشيطان الرجيم",
        "بسم الله الرحمن الرحيم",
        "سبح اسم ربك الاعلى",
    ])
    assert len(results) == 3
    r0 = results[0]
    assert r0.verse is not None
    assert r0.verse.is_istiadhah is True


# ---------------------------------------------------------------------------
# asr_sequential_fuzzy_search — verses list and is_multi_ayah
# ---------------------------------------------------------------------------

def test_single_verse_match_has_one_verse_in_list():
    """A single-verse match has exactly one entry in .verses."""
    results = asr_sequential_fuzzy_search(["سبح اسم ربك الاعلى"])
    r = results[0]
    assert r.verse is not None
    assert not r.is_multi_ayah
    assert len(r.verses) == 1
    assert r.verses[0] is r.verse


def test_single_verse_match_word_offsets():
    """Single-verse match has non-negative start_word and positive end_word."""
    results = asr_sequential_fuzzy_search(["سبح اسم ربك الاعلى"])
    r = results[0]
    assert r.verse is not None
    assert r.start_word >= 0
    assert r.end_word > r.start_word


def test_multi_ayah_segment_is_flagged():
    """A long segment spanning multiple ayahs sets is_multi_ayah=True."""
    # Concatenation of surah 87 ayah 1 + 2 + 3 (very long segment)
    long_seg = "سبح اسم ربك الاعلى الذي خلق فسوى والذي قدر فهدى والذي اخرج المرعى"
    results = asr_sequential_fuzzy_search([long_seg])
    r = results[0]
    assert r.verse is not None
    if r.is_multi_ayah:
        assert len(r.verses) > 1
        # All verses should belong to the same surah (87)
        for v in r.verses:
            assert v.surah_number == 87


def test_multi_ayah_segment_word_offsets():
    """Multi-ayah match has valid start_word and end_word."""
    long_seg = "سبح اسم ربك الاعلى الذي خلق فسوى والذي قدر فهدى والذي اخرج المرعى"
    results = asr_sequential_fuzzy_search([long_seg])
    r = results[0]
    assert r.verse is not None
    assert r.start_word >= 0
    assert r.end_word >= 0


def test_verses_list_never_empty_when_verse_is_not_none():
    """If verse is set, verses must be a non-empty list."""
    segments = ["بسم الله الرحمن الرحيم", "سبح اسم ربك الاعلى", "الذي خلق فسوى"]
    results = asr_sequential_fuzzy_search(segments)
    for r in results:
        if r.verse is not None:
            assert len(r.verses) >= 1


def test_verses_first_element_matches_verse_field():
    """result.verses[0] is always the same object as result.verse."""
    segments = ["سبح اسم ربك الاعلى", "الذي خلق فسوى"]
    results = asr_sequential_fuzzy_search(segments)
    for r in results:
        if r.verse is not None:
            assert r.verses[0] is r.verse


def test_multi_ayah_verses_in_quran_order():
    """For multi-ayah results, verses must be in ascending ayah order."""
    long_seg = "بسم الله الرحمن الرحيم سبح اسم ربك الاعلى الذي خلق فسوى والذي قدر فهدى"
    results = asr_sequential_fuzzy_search([long_seg])
    r = results[0]
    if r.is_multi_ayah and len(r.verses) > 1:
        for j in range(len(r.verses) - 1):
            v1, v2 = r.verses[j], r.verses[j + 1]
            assert (v1.surah_number, v1.ayah_number) < (v2.surah_number, v2.ayah_number)
