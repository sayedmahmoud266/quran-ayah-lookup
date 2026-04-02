"""
Unit tests for multi-database cache functionality in loader.py.

Tests the new behaviour where multiple QuranStyle databases coexist in the
global cache simultaneously without evicting one another.
"""
import pytest

from quran_ayah_lookup.loader import (
    get_quran_database,
    initialize_quran_database,
    switch_quran_style,
)
from quran_ayah_lookup.models import QuranStyle, QuranDatabase, QuranVerse
import quran_ayah_lookup.loader as loader_module


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def preload_simple_style():
    """
    Load the SIMPLE style into the cache once per test session.

    UTHMANI_ALL is already loaded at package-import time.  Preloading SIMPLE
    here avoids a cold-load penalty on every test that uses it.
    """
    get_quran_database(QuranStyle.SIMPLE)


@pytest.fixture
def restore_default_style():
    """Restore _default_style to its pre-test value after each test."""
    saved = loader_module._default_style
    yield
    loader_module._default_style = saved


# ---------------------------------------------------------------------------
# get_quran_database() — basic behaviour
# ---------------------------------------------------------------------------

def test_get_quran_database_no_args_returns_database():
    """get_quran_database() with no args returns a QuranDatabase."""
    db = get_quran_database()
    assert isinstance(db, QuranDatabase)


def test_get_quran_database_no_args_matches_default_style():
    """get_quran_database() returns the database for _default_style."""
    db = get_quran_database()
    assert db.corpus_style == loader_module._default_style


def test_get_quran_database_with_explicit_style_returns_correct_style():
    """get_quran_database(style) returns a database with that corpus_style."""
    db = get_quran_database(QuranStyle.UTHMANI_ALL)
    assert db.corpus_style == QuranStyle.UTHMANI_ALL


def test_get_quran_database_simple_style_returns_correct_style():
    """get_quran_database(SIMPLE) returns a database with corpus_style SIMPLE."""
    db = get_quran_database(QuranStyle.SIMPLE)
    assert db.corpus_style == QuranStyle.SIMPLE


# ---------------------------------------------------------------------------
# Caching / object identity
# ---------------------------------------------------------------------------

def test_get_quran_database_same_style_returns_same_object():
    """Calling get_quran_database(style) twice returns the identical object."""
    db1 = get_quran_database(QuranStyle.UTHMANI_ALL)
    db2 = get_quran_database(QuranStyle.UTHMANI_ALL)
    assert db1 is db2


def test_get_quran_database_no_args_returns_same_object():
    """Calling get_quran_database() twice without args returns the same object."""
    db1 = get_quran_database()
    db2 = get_quran_database()
    assert db1 is db2


def test_get_quran_database_simple_style_cached():
    """get_quran_database(SIMPLE) called twice returns the same object."""
    db1 = get_quran_database(QuranStyle.SIMPLE)
    db2 = get_quran_database(QuranStyle.SIMPLE)
    assert db1 is db2


def test_initialize_quran_database_uses_cache():
    """initialize_quran_database(style) returns the cached object on repeat calls."""
    db1 = initialize_quran_database(QuranStyle.UTHMANI_ALL)
    db2 = initialize_quran_database(QuranStyle.UTHMANI_ALL)
    assert db1 is db2


# ---------------------------------------------------------------------------
# Multiple databases coexist
# ---------------------------------------------------------------------------

def test_two_styles_are_distinct_objects():
    """Databases loaded for different styles are distinct objects."""
    db_uthmani = get_quran_database(QuranStyle.UTHMANI_ALL)
    db_simple = get_quran_database(QuranStyle.SIMPLE)
    assert db_uthmani is not db_simple


def test_two_styles_report_different_corpus_style():
    """Each cached database reports its own corpus_style."""
    db_uthmani = get_quran_database(QuranStyle.UTHMANI_ALL)
    db_simple = get_quran_database(QuranStyle.SIMPLE)
    assert db_uthmani.corpus_style != db_simple.corpus_style


def test_both_styles_present_in_cache():
    """After loading two styles, both appear in _quran_databases."""
    get_quran_database(QuranStyle.UTHMANI_ALL)
    get_quran_database(QuranStyle.SIMPLE)
    assert QuranStyle.UTHMANI_ALL in loader_module._quran_databases
    assert QuranStyle.SIMPLE in loader_module._quran_databases


def test_loading_explicit_style_does_not_change_default(restore_default_style):
    """get_quran_database(other_style) must not alter _default_style."""
    default_before = loader_module._default_style
    other = (QuranStyle.SIMPLE
             if default_before != QuranStyle.SIMPLE
             else QuranStyle.UTHMANI_ALL)
    get_quran_database(other)
    assert loader_module._default_style == default_before


# ---------------------------------------------------------------------------
# switch_quran_style
# ---------------------------------------------------------------------------

def test_switch_quran_style_returns_database(restore_default_style):
    """switch_quran_style() returns a QuranDatabase instance."""
    db = switch_quran_style(QuranStyle.SIMPLE)
    assert isinstance(db, QuranDatabase)


def test_switch_quran_style_returns_correct_corpus_style(restore_default_style):
    """switch_quran_style(style) returns the database for that style."""
    db = switch_quran_style(QuranStyle.SIMPLE)
    assert db.corpus_style == QuranStyle.SIMPLE


def test_switch_quran_style_updates_default_style_attribute(restore_default_style):
    """switch_quran_style updates loader_module._default_style."""
    switch_quran_style(QuranStyle.SIMPLE)
    assert loader_module._default_style == QuranStyle.SIMPLE


def test_switch_quran_style_makes_get_database_return_new_style(restore_default_style):
    """After switch_quran_style, get_quran_database() returns the new style."""
    switch_quran_style(QuranStyle.SIMPLE)
    db = get_quran_database()
    assert db.corpus_style == QuranStyle.SIMPLE


def test_switch_quran_style_preserves_old_db_in_cache(restore_default_style):
    """After switching style, the previous default is still accessible by style."""
    original_default = loader_module._default_style
    original_db = get_quran_database(original_default)

    other = (QuranStyle.SIMPLE
             if original_default != QuranStyle.SIMPLE
             else QuranStyle.UTHMANI_ALL)
    switch_quran_style(other)

    recovered = get_quran_database(original_default)
    assert recovered is original_db


def test_switch_quran_style_twice_ends_on_last_style(restore_default_style):
    """Switching style twice leaves the second style as the default."""
    switch_quran_style(QuranStyle.SIMPLE)
    switch_quran_style(QuranStyle.UTHMANI_ALL)
    db = get_quran_database()
    assert db.corpus_style == QuranStyle.UTHMANI_ALL


def test_switch_back_to_original_returns_same_cached_object(restore_default_style):
    """Switching away and back returns the same originally-cached object."""
    original_default = loader_module._default_style
    original_db = get_quran_database()

    other = (QuranStyle.SIMPLE
             if original_default != QuranStyle.SIMPLE
             else QuranStyle.UTHMANI_ALL)
    switch_quran_style(other)
    switch_quran_style(original_default)

    assert get_quran_database() is original_db


def test_switch_quran_style_returned_db_same_as_get_quran_database(restore_default_style):
    """The object returned by switch_quran_style equals get_quran_database(style)."""
    switched_db = switch_quran_style(QuranStyle.SIMPLE)
    fetched_db = get_quran_database(QuranStyle.SIMPLE)
    assert switched_db is fetched_db


# ---------------------------------------------------------------------------
# initialize_quran_database
# ---------------------------------------------------------------------------

def test_initialize_quran_database_no_args_returns_database():
    """initialize_quran_database() with no args returns a QuranDatabase."""
    db = initialize_quran_database()
    assert isinstance(db, QuranDatabase)


def test_initialize_quran_database_with_style_caches_result():
    """initialize_quran_database(style) stores the result in _quran_databases."""
    initialize_quran_database(QuranStyle.SIMPLE)
    assert QuranStyle.SIMPLE in loader_module._quran_databases


def test_initialize_quran_database_with_style_returns_correct_corpus_style():
    """initialize_quran_database(style) returns a db with the right corpus_style."""
    db = initialize_quran_database(QuranStyle.UTHMANI_ALL)
    assert db.corpus_style == QuranStyle.UTHMANI_ALL


def test_initialize_quran_database_result_same_as_get_quran_database():
    """initialize_quran_database(style) and get_quran_database(style) return the same object."""
    db_init = initialize_quran_database(QuranStyle.UTHMANI_ALL)
    db_get = get_quran_database(QuranStyle.UTHMANI_ALL)
    assert db_init is db_get


# ---------------------------------------------------------------------------
# Data consistency across databases
# ---------------------------------------------------------------------------

def test_total_surahs_same_across_two_styles():
    """Both loaded databases cover all 114 surahs."""
    db_uthmani = get_quran_database(QuranStyle.UTHMANI_ALL)
    db_simple = get_quran_database(QuranStyle.SIMPLE)
    assert db_uthmani.get_surah_count() == db_simple.get_surah_count() == 114


def test_verse_count_same_across_two_styles():
    """Both databases have the same number of non-basmala verses."""
    db_uthmani = get_quran_database(QuranStyle.UTHMANI_ALL)
    db_simple = get_quran_database(QuranStyle.SIMPLE)
    assert (db_uthmani.get_verse_count(include_basmalah=False) ==
            db_simple.get_verse_count(include_basmalah=False))


def test_get_verse_works_on_explicitly_loaded_style_db():
    """Normal verse operations work on a database loaded by explicit style."""
    db = get_quran_database(QuranStyle.SIMPLE)
    verse = db.get_verse(1, 1)
    assert isinstance(verse, QuranVerse)
    assert verse.surah_number == 1
    assert verse.ayah_number == 1


def test_default_db_and_explicit_db_agree_on_surah_count():
    """Default db and explicitly-fetched db of same style have the same surah count."""
    default_style = loader_module._default_style
    db_default = get_quran_database()
    db_explicit = get_quran_database(default_style)
    assert db_default.get_surah_count() == db_explicit.get_surah_count()
