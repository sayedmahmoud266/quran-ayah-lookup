"""
Quran data loader and initialization functionality.
"""
import os
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv

from .models import QuranVerse, QuranDatabase, QuranStyle, LoaderSettings, default_settings
from .text_utils import (
    normalize_arabic_text, 
    extract_basmala, 
    is_basmala_present, 
    remove_basmala_from_text,
    get_normalized_basmala
)

# ---------------------------------------------------------------------------
# Special verses — exist outside any corpus file
# ---------------------------------------------------------------------------

_ISTIADHAH_TEXT = "أَعُوذُ بِاللَّهِ مِنَ الشَّيْطَانِ الرَّجِيمِ"
ISTIADHAH_VERSE = QuranVerse(
    surah_number=0,
    ayah_number=0,
    text=_ISTIADHAH_TEXT,
    text_normalized=normalize_arabic_text(_ISTIADHAH_TEXT),
    is_basmalah=False,
    is_istiadhah=True,
    text_imlaai="أعوذ بالله من الشيطان الرجيم",
    alt={
        'simple-clean':   'اعوذ بالله من الشيطان الرجيم',
        'simple-minimal': 'اعوذ بالله من الشيطان الرجيم',
        'simple-plain':   'اعوذ بالله من الشيطان الرجيم',
        'simple':         'أعوذ بالله من الشيطان الرجيم',
        'uthmani':        'أَعُوذُ بِاللَّهِ مِنَ الشَّيْطَانِ الرَّجِيمِ',
    },
)

_TASDIQ_TEXT = "صَدَقَ اللَّهُ الْعَظِيمُ"
TASDIQ_VERSE = QuranVerse(
    surah_number=999,
    ayah_number=999,
    text=_TASDIQ_TEXT,
    text_normalized=normalize_arabic_text(_TASDIQ_TEXT),
    is_basmalah=False,
    is_tasdiq=True,
    text_imlaai="صدق الله العظيم",
    alt={
        'simple-clean':   'صدق الله العظيم',
        'simple-minimal': 'صدق الله العظيم',
        'simple-plain':   'صدق الله العظيم',
        'simple':         'صدق الله العظيم',
        'uthmani':        'صَدَقَ اللَّهُ الْعَظِيمُ',
    },
)


class QuranLoader:
    """Handles loading and processing of Quran text data."""
    
    # Surahs that don't have Basmala at the beginning
    SURAHS_WITHOUT_BASMALA = {1, 9}  # Al-Fatihah and At-Tawbah

    # Alt corpora to merge into each QuranVerse (key → QuranStyle)
    ALT_CORPORA: Dict[str, 'QuranStyle'] = {
        'simple-clean':   QuranStyle.SIMPLE_CLEAN,
        'simple-minimal': QuranStyle.SIMPLE_MINIMAL,
        'simple-plain':   QuranStyle.SIMPLE_PLAIN,
        'simple':         QuranStyle.SIMPLE,
        'uthmani':        QuranStyle.UTHMANI,
    }
    IMLAAI_CORPUS = QuranStyle.SIMPLE_IMLAAI

    def __init__(self):
        """Initialize the loader. Always uses UTHMANI_ALL as the primary corpus."""
        self._load_env()
        self.style = QuranStyle.UTHMANI_ALL
        self.data_file_path = self._get_data_file_path(QuranStyle.UTHMANI_ALL)

    def _load_env(self):
        """Load environment variables for cache and autoload configuration."""
        load_dotenv()

        global default_settings

        cache_enabled_str = os.getenv("QAL_CACHE_ENABLED", str(default_settings.cache_enabled)).lower()
        autoload_on_import_str = os.getenv("QAL_AUTOLOAD_ON_IMPORT", str(default_settings.autoload_on_import)).lower()

        try:
            default_settings.cache_enabled = cache_enabled_str in ("1", "true", "yes")
        except Exception:
            default_settings.cache_enabled = True

        try:
            default_settings.autoload_on_import = autoload_on_import_str in ("1", "true", "yes")
        except Exception:
            default_settings.autoload_on_import = True
        
    def _get_data_file_path(self, style: QuranStyle) -> Path:
        """Resolve the resource file path for the given QuranStyle."""
        data_file_dir = Path(__file__).parent / "resources"
        data_file_path = data_file_dir / style.value
        if not data_file_path.exists():
            raise FileNotFoundError(
                f"Quran data file not found at {data_file_path}. "
                f"Please ensure {style.name} exists in the resources directory."
            )
        return data_file_path

    def _load_alt_corpus_lookup(self, style: QuranStyle) -> Dict:
        """
        Parse an alternate corpus file into a {(surah, ayah): text} lookup dict.

        Applies the same Basmala-splitting logic as the primary loader so that
        ayah 0 (Basmala) and ayah 1 (remainder) are keyed correctly for every
        surah that carries a Basmala (i.e. all except surahs 1 and 9).

        Args:
            style: The QuranStyle whose resource file to open.

        Returns:
            Dict mapping (surah_number, ayah_number) -> raw text string.
        """
        file_path = self._get_data_file_path(style)
        lookup: Dict = {}

        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or line.startswith('='):
                    continue
                parts = line.split('|')
                if len(parts) != 3:
                    continue
                try:
                    surah_num = int(parts[0])
                    ayah_num = int(parts[1])
                    text = parts[2]
                except ValueError:
                    continue

                # Non-Basmala surahs or non-first ayahs: store as-is
                if surah_num in self.SURAHS_WITHOUT_BASMALA or ayah_num != 1:
                    lookup[(surah_num, ayah_num)] = text
                    continue

                # First ayah of other surahs: split out Basmala (ayah 0) from remainder (ayah 1)
                if is_basmala_present(text):
                    remainder = remove_basmala_from_text(text)
                    if remainder and remainder in text:
                        split_idx = text.find(remainder)
                        alt_basmala = text[:split_idx].strip()
                    else:
                        alt_basmala = text
                        remainder = ''
                    lookup[(surah_num, 0)] = alt_basmala
                    if remainder:
                        lookup[(surah_num, 1)] = remainder
                else:
                    lookup[(surah_num, ayah_num)] = text

        return lookup

    def load_quran_data(self) -> QuranDatabase:
        """
        Load and process all Quran verses.

        Phase 1 — primary corpus (quran-uthmani_all.txt): builds the full
        QuranDatabase with text / text_normalized / Basmala extraction.

        Phase 2 — alt corpora: populates verse.alt[key] for each of the five
        alternate text variants (simple-clean, simple-minimal, simple-plain,
        simple, uthmani).

        Phase 3 — imlaai corpus: populates verse.text_imlaai.

        Returns:
            QuranDatabase: Complete database with all verses and alt texts.
        """
        # ── Phase 1: primary load ────────────────────────────────────────────
        database = QuranDatabase()
        database.corpus_style = self.style

        with open(self.data_file_path, 'r', encoding='utf-8') as file:
            for line_number, line in enumerate(file, 1):
                line = line.strip()

                if not line or line.startswith('#') or line.startswith('='):
                    continue

                try:
                    verse = self._parse_verse_line(line)
                    processed_verses = self._process_verse(verse)
                    for processed_verse in processed_verses:
                        database.add_verse(processed_verse)
                except Exception as e:
                    raise ValueError(
                        f"Error processing line {line_number}: {line}. "
                        f"Error: {str(e)}"
                    )

        # ── Phase 2: alt corpora ─────────────────────────────────────────────
        for alt_key, alt_style in self.ALT_CORPORA.items():
            try:
                alt_lookup = self._load_alt_corpus_lookup(alt_style)
                for surah in database.surahs.values():
                    for verse in surah.ayahs.values():
                        verse.alt[alt_key] = alt_lookup.get(
                            (verse.surah_number, verse.ayah_number)
                        )
            except FileNotFoundError:
                pass  # alt corpus missing — leave None values

        # ── Phase 3: imlaai corpus ───────────────────────────────────────────
        try:
            imlaai_lookup = self._load_alt_corpus_lookup(self.IMLAAI_CORPUS)
            for surah in database.surahs.values():
                for verse in surah.ayahs.values():
                    verse.text_imlaai = imlaai_lookup.get(
                        (verse.surah_number, verse.ayah_number)
                    )
        except FileNotFoundError:
            pass  # imlaai corpus missing — leave None values

        # ── Phase 4: inject special verses ──────────────────────────────────
        database.register_special_verse(ISTIADHAH_VERSE)
        database.register_special_verse(TASDIQ_VERSE)

        return database
    
    def _parse_verse_line(self, line: str) -> QuranVerse:
        """
        Parse a single line from the text file into a QuranVerse.
        
        Args:
            line: Line in format "surah_number|ayah_number|text"
            
        Returns:
            QuranVerse: Parsed verse (before Basmala processing)
        """
        parts = line.split('|')
        if len(parts) != 3:
            raise ValueError(f"Invalid line format. Expected 3 parts, got {len(parts)}")
        
        try:
            surah_number = int(parts[0])
            ayah_number = int(parts[1])
            text = parts[2]
        except ValueError as e:
            raise ValueError(f"Invalid number format: {e}")
        
        if not (1 <= surah_number <= 114):
            raise ValueError(f"Invalid surah number: {surah_number}")
        
        if ayah_number < 1:
            raise ValueError(f"Invalid ayah number: {ayah_number}")
        
        # Create initial verse with normalized text
        normalized_text = normalize_arabic_text(text)
        
        return QuranVerse(
            surah_number=surah_number,
            ayah_number=ayah_number,
            text=text,
            text_normalized=normalized_text,
            is_basmalah=False
        )
    
    def _process_verse(self, verse: QuranVerse) -> List[QuranVerse]:
        """
        Process a verse to handle Basmala extraction if needed.
        
        Args:
            verse: Original verse from file
            
        Returns:
            List[QuranVerse]: One or two verses (Basmala + main verse if applicable)
        """
        # Al-Fatihah (1) and At-Tawbah (9) don't need Basmala processing
        if verse.surah_number in self.SURAHS_WITHOUT_BASMALA:
            return [verse]
        
        # Only process first ayah of other surahs for Basmala extraction
        if verse.ayah_number != 1:
            return [verse]
        
        # Check if this verse contains Basmala
        if not is_basmala_present(verse.text):
            # This shouldn't happen for most surahs, but handle gracefully
            return [verse]
        
        # Extract Basmala and remaining text
        basmala_text = extract_basmala()
        remaining_text = remove_basmala_from_text(verse.text)
        
        verses_to_return = []
        
        # Create Basmala verse (ayah number 0)
        basmala_verse = QuranVerse(
            surah_number=verse.surah_number,
            ayah_number=0,
            text=basmala_text,
            text_normalized=get_normalized_basmala(),
            is_basmalah=True
        )
        verses_to_return.append(basmala_verse)
        
        # Create main verse with remaining text (keep original ayah number)
        if remaining_text:  # Only if there's text after Basmala
            main_verse = QuranVerse(
                surah_number=verse.surah_number,
                ayah_number=verse.ayah_number,
                text=remaining_text,
                text_normalized=normalize_arabic_text(remaining_text),
                is_basmalah=False
            )
            verses_to_return.append(main_verse)
        
        return verses_to_return


# Single unified cached database (all corpus variants merged into each QuranVerse)
_quran_database: Optional[QuranDatabase] = None


def initialize_quran_database(_style: QuranStyle = None) -> QuranDatabase:
    """
    Initialize and load the unified Quran database.

    Loads the primary corpus (quran-uthmani_all.txt) and merges all alternate
    corpus texts inline into every QuranVerse.  Subsequent calls return the
    cached instance regardless of the ``_style`` argument (which is kept for
    call-site compatibility but is no longer used).

    Returns:
        QuranDatabase: The loaded Quran database.
    """
    global _quran_database
    global default_settings

    if _quran_database is not None:
        return _quran_database

    loader = QuranLoader()
    db = loader.load_quran_data()

    if default_settings.cache_enabled:
        db.finalize_cache()

    print(f"✓ Quran database loaded successfully:")
    print(f"  - Primary corpus: {db.corpus_style.name} ({db.corpus_style.value})")
    print(f"  - Alt corpora merged: {', '.join(QuranLoader.ALT_CORPORA.keys())}, imlaai")
    print(f"  - Total verses: {db.total_verses}")
    print(f"  - Total surahs: {db.total_surahs}")
    print(f"  - Source: Tanzil.net")
    if default_settings.cache_enabled:
        print(f"  - Performance cache: enabled")

    _quran_database = db
    return db


def get_quran_database(_style: QuranStyle = None) -> QuranDatabase:
    """
    Return the unified Quran database, initializing it on first call.

    The ``_style`` argument is accepted for call-site compatibility but is
    no longer used — the database always contains all corpus variants merged
    inline into each QuranVerse.

    Returns:
        QuranDatabase: The unified database.
    """
    if _quran_database is not None:
        return _quran_database
    return initialize_quran_database()


def update_loader_settings(new_settings: LoaderSettings):
    """
    Update the loader settings used during Quran database initialization.

    Args:
        new_settings (LoaderSettings): New settings to apply.
    """
    global default_settings
    default_settings = new_settings