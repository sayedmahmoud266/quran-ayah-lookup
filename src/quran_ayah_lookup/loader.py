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


class QuranLoader:
    """Handles loading and processing of Quran text data."""
    
    # Surahs that don't have Basmala at the beginning
    SURAHS_WITHOUT_BASMALA = {1, 9}  # Al-Fatihah and At-Tawbah

    style: QuranStyle
    
    def __init__(self, _style: QuranStyle = None):
        """Initialize the loader with specified style and load environment settings."""
        self._load_env()
        # An explicit style argument takes precedence over the env-configured default
        if _style is not None:
            self.style = _style
        self.data_file_path = self._get_data_file_path(_style)

    def _load_env(self):
        """Load environment variables for configuration."""
        load_dotenv()

        global default_settings

        # check settings from env variables
        style_str = os.getenv("QAL_STYLE", default_settings.style.name).upper()
        cache_enabled_str = os.getenv("QAL_CACHE_ENABLED", str(default_settings.cache_enabled)).lower()
        autoload_on_import_str = os.getenv("QAL_AUTOLOAD_ON_IMPORT", str(default_settings.autoload_on_import)).lower()

        try:
            self.style = QuranStyle[style_str]
            default_settings.style = self.style
        except KeyError:
            print(f"Invalid QAL_STYLE specified. Falling back to default: {default_settings.style.name}")
            self.style = default_settings.style

        try:
            default_settings.cache_enabled = cache_enabled_str in ("1", "true", "yes")
        except Exception:
            default_settings.cache_enabled = True

        try:
            default_settings.autoload_on_import = autoload_on_import_str in ("1", "true", "yes")
        except Exception:
            default_settings.autoload_on_import = True
        
    def _get_data_file_path(self, _style: QuranStyle = None) -> Path:
        """Get the path to the quran-uthmani_all.txt file."""
        current_dir = Path(__file__).parent
        data_file_dir = current_dir / "resources"

        data_file = _style or self.style

        print(f"Using Quran data file: {data_file.value}, style(override): {_style.name if _style else 'None'}, self.style: {self.style.name}")
        data_file_path = data_file_dir / str(data_file.value)
        
        if not data_file_path.exists():
            raise FileNotFoundError(
                f"Quran data file not found at {data_file_path}. "
                f"Please ensure {data_file.name} exists in the resources directory."
            )
        
        return data_file_path
    
    def load_quran_data(self) -> QuranDatabase:
        """
        Load and process all Quran verses from the text file.
        
        Returns:
            QuranDatabase: Complete database with all verses processed
        """
        database = QuranDatabase()
        database.corpus_style = self.style
        
        with open(self.data_file_path, 'r', encoding='utf-8') as file:
            for line_number, line in enumerate(file, 1):
                line = line.strip()
                
                # Skip empty lines and comments/copyright lines
                if not line or line.startswith('#') or line.startswith('='):
                    continue
                
                try:
                    verse = self._parse_verse_line(line)
                    processed_verses = self._process_verse(verse)
                    
                    # Add all processed verses to the database
                    for processed_verse in processed_verses:
                        database.add_verse(processed_verse)
                    
                except Exception as e:
                    raise ValueError(
                        f"Error processing line {line_number}: {line}. "
                        f"Error: {str(e)}"
                    )
        
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


# Cache of all loaded databases keyed by style
_quran_databases: Dict[QuranStyle, QuranDatabase] = {}

# The current default style (None until first initialization)
_default_style: Optional[QuranStyle] = None


def initialize_quran_database(_style: QuranStyle = None) -> QuranDatabase:
    """
    Initialize and load the Quran database.
    This function is called once per style; subsequent calls return the cached instance.

    If _style is None, the default style is determined from environment variables
    (QAL_STYLE) or the current default_settings.

    Returns:
        QuranDatabase: The loaded Quran database
    """
    global _quran_databases
    global _default_style
    global default_settings

    # Create the loader — this triggers _load_env() which reads env vars and
    # updates default_settings.style to the env-configured value.
    loader = QuranLoader(_style)

    # Determine the effective style:
    #   • if the caller explicitly requested a style, use that
    #   • otherwise use the env/settings-configured default
    effective_style = _style if _style is not None else default_settings.style

    # Track the default style (first call without an explicit style wins unless
    # switch_quran_style() has already been called)
    if _default_style is None:
        _default_style = effective_style

    # Return from cache if already loaded
    if effective_style in _quran_databases:
        return _quran_databases[effective_style]

    # Load and cache
    db = loader.load_quran_data()

    if default_settings.cache_enabled:
        db.finalize_cache()

    print(f"✓ Quran database loaded successfully:")
    print(f"  - Style: {db.corpus_style.name}, file: {db.corpus_style.value}")
    print(f"  - Total verses: {db.total_verses}")
    print(f"  - Total surahs: {db.total_surahs}")
    print(f"  - Source: Tanzil.net")
    if default_settings.cache_enabled:
        print(f"  - Performance cache: enabled")

    _quran_databases[effective_style] = db
    return db


def get_quran_database(_style: QuranStyle = None) -> QuranDatabase:
    """
    Get the Quran database.

    • Called without arguments → returns the default configured database
      (loading it on first call if necessary).
    • Called with a QuranStyle → returns that specific database, loading and
      caching it if it has not been loaded yet. The default is not changed.

    Returns:
        QuranDatabase: The requested database
    """
    if _style is None:
        # Return default database, initialising if needed
        if _default_style is not None and _default_style in _quran_databases:
            return _quran_databases[_default_style]
        return initialize_quran_database(None)

    # Specific style requested — serve from cache or load
    if _style not in _quran_databases:
        return initialize_quran_database(_style)
    return _quran_databases[_style]


def switch_quran_style(new_style: QuranStyle) -> QuranDatabase:
    """
    Switch the default Quran database to a different style.

    The new style is loaded and cached if not already done.  All previously
    loaded databases remain available in the cache; nothing is discarded.

    Args:
        new_style (QuranStyle): The style to make the new default.

    Returns:
        QuranDatabase: The Quran database for the new style.
    """
    global _default_style
    _default_style = new_style
    return get_quran_database(new_style)


def update_loader_settings(new_settings: LoaderSettings):
    """
    Update the loader settings used during Quran database initialization.

    Args:
        new_settings (LoaderSettings): New settings to apply.
    """
    global default_settings
    default_settings = new_settings