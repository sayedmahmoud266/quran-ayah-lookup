"""
Tests for the unified Quran database introduced by the merged-corpus refactor.

The old multi-database / style-switching behaviour has been replaced by a
single QuranDatabase whose QuranVerse objects carry all corpus variants inline:
  - verse.alt  — dict with keys: simple-clean, simple-minimal, simple-plain, simple, uthmani
  - verse.text_imlaai — dedicated imlaai field

All search/retrieval functions are unchanged and operate on the primary
(quran-uthmani_all.txt) text as before.
"""
import pytest

from quran_ayah_lookup.loader import (
    get_quran_database,
    initialize_quran_database,
)
from quran_ayah_lookup.models import QuranStyle, QuranDatabase, QuranVerse
import quran_ayah_lookup.loader as loader_module


# ---------------------------------------------------------------------------
# Expected alt corpus keys
# ---------------------------------------------------------------------------

EXPECTED_ALT_KEYS = {'simple-clean', 'simple-minimal', 'simple-plain', 'simple', 'uthmani'}


# ---------------------------------------------------------------------------
# Single unified database
# ---------------------------------------------------------------------------

def test_get_quran_database_no_args_returns_database():
    """get_quran_database() with no args returns a QuranDatabase."""
    db = get_quran_database()
    assert isinstance(db, QuranDatabase)


def test_get_quran_database_with_style_arg_returns_same_database():
    """Passing any QuranStyle to get_quran_database returns the unified DB."""
    db_default = get_quran_database()
    db_with_style = get_quran_database(QuranStyle.SIMPLE_CLEAN)
    assert db_default is db_with_style


def test_get_quran_database_all_styles_return_same_object():
    """All QuranStyle values return the identical unified database object."""
    db_ref = get_quran_database()
    for style in QuranStyle:
        assert get_quran_database(style) is db_ref


def test_get_quran_database_returns_same_object_on_repeated_calls():
    """Calling get_quran_database() multiple times returns the same instance."""
    db1 = get_quran_database()
    db2 = get_quran_database()
    assert db1 is db2


def test_initialize_quran_database_returns_same_cached_object():
    """initialize_quran_database() returns the already-cached instance."""
    db1 = initialize_quran_database()
    db2 = initialize_quran_database()
    assert db1 is db2


def test_initialize_quran_database_style_arg_ignored():
    """initialize_quran_database(style) returns the same unified DB."""
    db_no_arg = initialize_quran_database()
    db_with_style = initialize_quran_database(QuranStyle.UTHMANI)
    assert db_no_arg is db_with_style


# ---------------------------------------------------------------------------
# Primary corpus is always UTHMANI_ALL
# ---------------------------------------------------------------------------

def test_corpus_style_is_uthmani_all():
    """The unified database always reports corpus_style = UTHMANI_ALL."""
    db = get_quran_database()
    assert db.corpus_style == QuranStyle.UTHMANI_ALL


def test_database_has_114_surahs():
    """Database contains all 114 surahs."""
    db = get_quran_database()
    assert db.get_surah_count() == 114


# ---------------------------------------------------------------------------
# alt dict on QuranVerse
# ---------------------------------------------------------------------------

def test_verse_has_alt_dict():
    """Every verse has an alt dict."""
    db = get_quran_database()
    verse = db.get_verse(1, 1)
    assert hasattr(verse, 'alt')
    assert isinstance(verse.alt, dict)


def test_verse_alt_has_expected_keys():
    """verse.alt contains all five expected corpus keys."""
    db = get_quran_database()
    verse = db.get_verse(2, 1)
    assert set(verse.alt.keys()) == EXPECTED_ALT_KEYS


def test_verse_alt_values_populated():
    """alt values are non-None strings for a regular verse."""
    db = get_quran_database()
    verse = db.get_verse(2, 1)
    for key in EXPECTED_ALT_KEYS:
        assert verse.alt[key] is not None, f"alt['{key}'] is None for verse 2:1"
        assert isinstance(verse.alt[key], str)
        assert len(verse.alt[key]) > 0


def test_verse_alt_basmala_populated():
    """alt values are non-None for Basmala verses (ayah 0)."""
    db = get_quran_database()
    basmala = db.get_verse(2, 0)
    assert basmala.is_basmalah
    for key in EXPECTED_ALT_KEYS:
        assert basmala.alt[key] is not None, f"alt['{key}'] is None for Basmala 2:0"


def test_verse_alt_at_tawbah_no_basmala():
    """At-Tawbah (9:1) alt values are populated (no Basmala in this surah)."""
    db = get_quran_database()
    verse = db.get_verse(9, 1)
    assert not verse.is_basmalah
    for key in EXPECTED_ALT_KEYS:
        assert verse.alt[key] is not None, f"alt['{key}'] is None for verse 9:1"


def test_verse_alt_values_are_arabic_text():
    """Alt values contain Arabic characters."""
    db = get_quran_database()
    verse = db.get_verse(1, 1)
    for key in EXPECTED_ALT_KEYS:
        # Arabic Unicode block: U+0600–U+06FF
        assert any('\u0600' <= ch <= '\u06ff' for ch in (verse.alt[key] or '')), \
            f"alt['{key}'] doesn't contain Arabic text"


def test_verse_alt_simple_clean_differs_from_primary():
    """simple-clean text is different from the primary uthmani-all text (no diacritics)."""
    db = get_quran_database()
    verse = db.get_verse(2, 1)
    # Primary has full diacritics; simple-clean should not
    assert verse.alt['simple-clean'] != verse.text


# ---------------------------------------------------------------------------
# text_imlaai field on QuranVerse
# ---------------------------------------------------------------------------

def test_verse_has_text_imlaai():
    """Every verse has a text_imlaai attribute."""
    db = get_quran_database()
    verse = db.get_verse(1, 1)
    assert hasattr(verse, 'text_imlaai')


def test_verse_text_imlaai_populated():
    """text_imlaai is a non-None string for a regular verse."""
    db = get_quran_database()
    verse = db.get_verse(2, 1)
    assert verse.text_imlaai is not None
    assert isinstance(verse.text_imlaai, str)
    assert len(verse.text_imlaai) > 0


def test_verse_text_imlaai_basmala_populated():
    """text_imlaai is populated for Basmala verses."""
    db = get_quran_database()
    basmala = db.get_verse(2, 0)
    assert basmala.is_basmalah
    assert basmala.text_imlaai is not None


def test_verse_text_imlaai_at_tawbah():
    """text_imlaai is populated for At-Tawbah ayah 1 (no Basmala)."""
    db = get_quran_database()
    verse = db.get_verse(9, 1)
    assert verse.text_imlaai is not None


# ---------------------------------------------------------------------------
# to_dict includes new fields
# ---------------------------------------------------------------------------

def test_verse_to_dict_includes_alt_and_imlaai():
    """QuranVerse.to_dict() includes 'alt' and 'text_imlaai' keys."""
    db = get_quran_database()
    verse = db.get_verse(2, 1)
    d = verse.to_dict()
    assert 'alt' in d
    assert 'text_imlaai' in d
    assert set(d['alt'].keys()) == EXPECTED_ALT_KEYS


# ---------------------------------------------------------------------------
# switch_quran_style is removed
# ---------------------------------------------------------------------------

def test_switch_quran_style_not_importable():
    """switch_quran_style no longer exists in the loader module."""
    assert not hasattr(loader_module, 'switch_quran_style')


# ---------------------------------------------------------------------------
# Special verses — Istia'dhah (0:0) and Tasdiq (999:999)
# ---------------------------------------------------------------------------

def test_get_verse_istiadhah():
    """get_verse(0, 0) returns the Istia'dhah verse."""
    db = get_quran_database()
    verse = db.get_verse(0, 0)
    assert verse.is_istiadhah is True
    assert verse.surah_number == 0
    assert verse.ayah_number == 0


def test_get_verse_tasdiq():
    """get_verse(999, 999) returns the Tasdiq verse."""
    db = get_quran_database()
    verse = db.get_verse(999, 999)
    assert verse.is_tasdiq is True
    assert verse.surah_number == 999
    assert verse.ayah_number == 999


def test_istiadhah_not_in_surahs():
    """Surah 0 must not appear in db.surahs."""
    db = get_quran_database()
    assert 0 not in db.surahs


def test_tasdiq_not_in_surahs():
    """Surah 999 must not appear in db.surahs."""
    db = get_quran_database()
    assert 999 not in db.surahs


def test_get_all_verses_excludes_special():
    """get_all_verses() must not include Istia'dhah or Tasdiq."""
    db = get_quran_database()
    for verse in db.get_all_verses():
        assert not verse.is_istiadhah
        assert not verse.is_tasdiq


def test_verse_count_excludes_special():
    """get_verse_count() is unchanged by special verses."""
    db = get_quran_database()
    # Standard Quran corpus has 6236 non-basmalah verses
    count = db.get_verse_count(include_basmalah=False)
    assert count == 6236


def test_istiadhah_flags():
    """is_istiadhah=True; is_basmalah and is_tasdiq are False."""
    db = get_quran_database()
    verse = db.get_verse(0, 0)
    assert verse.is_istiadhah is True
    assert verse.is_basmalah is False
    assert verse.is_tasdiq is False


def test_tasdiq_flags():
    """is_tasdiq=True; is_basmalah and is_istiadhah are False."""
    db = get_quran_database()
    verse = db.get_verse(999, 999)
    assert verse.is_tasdiq is True
    assert verse.is_basmalah is False
    assert verse.is_istiadhah is False


def test_special_verses_have_alt_keys():
    """Both special verses carry all 5 alt keys."""
    db = get_quran_database()
    for ref in [(0, 0), (999, 999)]:
        verse = db.get_verse(*ref)
        assert set(verse.alt.keys()) == EXPECTED_ALT_KEYS
        for v in verse.alt.values():
            assert v is not None


def test_special_verses_have_text_imlaai():
    """Both special verses carry a non-empty text_imlaai."""
    db = get_quran_database()
    for ref in [(0, 0), (999, 999)]:
        verse = db.get_verse(*ref)
        assert verse.text_imlaai is not None
        assert len(verse.text_imlaai) > 0


def test_to_dict_includes_istiadhah_flag():
    """to_dict() on Istia'dhah verse includes is_istiadhah=True."""
    db = get_quran_database()
    d = db.get_verse(0, 0).to_dict()
    assert d['is_istiadhah'] is True
    assert d['is_tasdiq'] is False


def test_to_dict_includes_tasdiq_flag():
    """to_dict() on Tasdiq verse includes is_tasdiq=True."""
    db = get_quran_database()
    d = db.get_verse(999, 999).to_dict()
    assert d['is_tasdiq'] is True
    assert d['is_istiadhah'] is False


def test_regular_verse_flags_are_false():
    """Regular corpus verses have both special flags set to False."""
    db = get_quran_database()
    verse = db.get_verse(2, 1)
    assert verse.is_istiadhah is False
    assert verse.is_tasdiq is False


def test_search_text_finds_istiadhah_at_front():
    """search_text for istia'dhah text returns it at index 0."""
    db = get_quran_database()
    results = db.search_text("اعوذ بالله", normalized=True)
    assert len(results) >= 1
    assert results[0].is_istiadhah is True


def test_search_text_finds_tasdiq_at_end():
    """search_text for tasdiq text returns it as last result."""
    db = get_quran_database()
    results = db.search_text("صدق الله", normalized=True)
    assert len(results) >= 1
    assert results[-1].is_tasdiq is True


def test_search_text_istiadhah_standalone():
    """Standalone search for exact istia'dhah phrase returns it."""
    db = get_quran_database()
    results = db.search_text("اعوذ بالله من الشيطان الرجيم", normalized=True)
    assert any(v.is_istiadhah for v in results)


def test_search_text_tasdiq_standalone():
    """Standalone search for exact tasdiq phrase returns it."""
    db = get_quran_database()
    results = db.search_text("صدق الله العظيم", normalized=True)
    assert any(v.is_tasdiq for v in results)


def test_fuzzy_search_finds_istiadhah_at_front():
    """fuzzy_search for istia'dhah phrase returns it at index 0."""
    db = get_quran_database()
    results = db.fuzzy_search("اعوذ بالله من الشيطان الرجيم", threshold=0.7, normalized=True)
    assert len(results) >= 1
    assert results[0].verse.is_istiadhah is True


def test_fuzzy_search_finds_tasdiq_at_end():
    """fuzzy_search for tasdiq phrase returns it as last result."""
    db = get_quran_database()
    results = db.fuzzy_search("صدق الله العظيم", threshold=0.7, normalized=True)
    assert len(results) >= 1
    assert results[-1].verse.is_tasdiq is True


def test_istiadhah_not_in_middle_of_results():
    """When other results exist, Istia'dhah is pinned to index 0, not middle."""
    db = get_quran_database()
    results = db.search_text("اعوذ بالله", normalized=True)
    if len(results) > 1:
        for v in results[1:]:
            assert not v.is_istiadhah


def test_tasdiq_not_in_middle_of_results():
    """When other results exist, Tasdiq is pinned to last position, not middle."""
    db = get_quran_database()
    results = db.search_text("صدق الله", normalized=True)
    if len(results) > 1:
        for v in results[:-1]:
            assert not v.is_tasdiq
