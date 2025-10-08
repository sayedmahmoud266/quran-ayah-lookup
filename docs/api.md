# API Reference

## Overview

This document provides detailed API reference for the Quran Ayah Lookup package with O(1) performance.

## Quick Reference

```python
import quran_ayah_lookup as qal

# O(1) Direct access
db = qal.get_quran_database()
verse = db[surah][ayah]

# Convenience functions  
verse = qal.get_verse(surah, ayah)
surah = qal.get_surah(surah_number)
results = qal.search_text(query)
```

## Core Functions

### get_verse(surah_number: int, ayah_number: int) → QuranVerse

Get a specific verse by surah and ayah number.

```python
verse = qal.get_verse(3, 35)  # Al-Imran, verse 35
```

**Parameters:**
- `surah_number` (int): Surah number (1-114)
- `ayah_number` (int): Ayah number (0 for Basmala, 1+ for regular ayahs)

**Returns:** `QuranVerse` object

**Raises:** `ValueError` if verse not found

### get_surah(surah_number: int) → QuranChapter

Get a surah/chapter with O(1) verse access.

```python
surah = qal.get_surah(3)  # Get Al-Imran
verse = surah[35]         # O(1) access to verse 35
```

**Parameters:**
- `surah_number` (int): Surah number (1-114)

**Returns:** `QuranChapter` object

**Raises:** `ValueError` if surah not found

### search_text(query: str, normalized: bool = True) → List[QuranVerse]

Search for verses containing the query text.

```python
results = qal.search_text("الله", normalized=True)
```

**Parameters:**
- `query` (str): Arabic text to search for
- `normalized` (bool): Search in normalized text (default: True)

**Returns:** List of matching `QuranVerse` objects

### get_surah_verses(surah_number: int) → List[QuranVerse]

Get all verses from a specific surah.

```python
verses = qal.get_surah_verses(1)  # All verses from Al-Fatihah
```

**Parameters:**
- `surah_number` (int): Surah number (1-114)

**Returns:** List of `QuranVerse` objects (including Basmala if present)

### normalize_arabic_text(text: str) → str

Normalize Arabic text by removing diacritics and normalizing Alif characters.

```python
normalized = qal.normalize_arabic_text("بِسْمِ ٱللَّهِ")
# Result: "بسم الله"
```

**Parameters:**
- `text` (str): Original Arabic text with diacritics

**Returns:** Normalized Arabic text without diacritics

### get_quran_database() → QuranDatabase

Get the main database instance (loaded automatically on import).

```python
db = qal.get_quran_database()
verse = db[3][35]  # Direct O(1) access
```

**Returns:** `QuranDatabase` object

## Data Models

### QuranVerse

Represents a single verse from the Quran.

```python
verse = qal.get_verse(1, 1)
print(f"Surah: {verse.surah_number}")
print(f"Ayah: {verse.ayah_number}")
print(f"Text: {verse.text}")
print(f"Normalized: {verse.text_normalized}")
print(f"Is Basmala: {verse.is_basmalah}")
```

**Attributes:**
- `surah_number` (int): Surah number (1-114)
- `ayah_number` (int): Ayah number (0 for Basmala, 1+ for regular ayahs)
- `text` (str): Original Arabic text with diacritics
- `text_normalized` (str): Normalized Arabic text without diacritics
- `is_basmalah` (bool): True if this is a Basmala verse

### QuranChapter

Represents a Quran chapter (surah) with O(1) verse lookup.

```python
surah = qal.get_surah(2)  # Al-Baqarah

# O(1) operations
verse = surah[255]        # Get Ayat al-Kursi
has_verse = 255 in surah  # Check existence  
count = len(surah)        # Get verse count

# Methods
all_verses = surah.get_all_verses()
verse_count = surah.get_verse_count()
has_basmala = surah.has_basmala()
```

**Attributes:**
- `number` (int): Surah number (1-114)
- `ayahs` (Dict[int, QuranVerse]): Dictionary mapping ayah number to verse

**Methods:**
- `get_verse(ayah_number)` → QuranVerse: Get specific verse (O(1))
- `get_all_verses()` → List[QuranVerse]: Get all verses as ordered list
- `get_verse_count()` → int: Get total verse count
- `has_basmala()` → bool: Check if surah has Basmala (ayah 0)

**Special Methods:**
- `len(chapter)`: Get verse count
- `ayah_number in chapter`: Check if ayah exists (O(1))
- `chapter[ayah_number]`: Get verse directly (O(1))

### QuranDatabase

Main database containing all Quran chapters with O(1) lookup.

```python
db = qal.get_quran_database()

# Direct access (fastest)
verse = db[3][35]  # O(1) lookup

# Information
print(f"Total verses: {len(db)}")
print(f"Total surahs: {db.total_surahs}")

# Check existence
if 3 in db:
    surah = db[3]
```

**Attributes:**
- `surahs` (Dict[int, QuranChapter]): Dictionary mapping surah number to chapter
- `total_verses` (int): Total number of verses (6,348 including Basmalas)
- `total_surahs` (int): Total number of surahs (114)

**Methods:**
- `get_verse(surah_number, ayah_number)` → QuranVerse: Get specific verse (O(1))
- `get_surah(surah_number)` → QuranChapter: Get specific surah (O(1))
- `get_all_verses()` → List[QuranVerse]: Get all verses as ordered list
- `search_text(query, normalized)` → List[QuranVerse]: Search for text

**Special Methods:**
- `len(db)`: Get total verse count
- `surah_number in db`: Check if surah exists (O(1))
- `db[surah_number]`: Get surah directly (O(1))

## Performance Reference

### O(1) Operations
All these operations complete in constant time regardless of database size:

- `db[surah][ayah]` - Direct verse access
- `surah[ayah]` - Verse access within surah  
- `ayah in surah` - Existence check
- `surah in db` - Surah existence check
- `len(surah)` - Verse count
- `len(db)` - Total verse count

### Performance Metrics
```
Operation           | Time (1000x) | Complexity
--------------------|---------------|------------
O(1) lookup         | 0.0006s      | O(1)
Linear search       | 0.5725s      | O(n)
Speedup             | 956x faster  | -
```

## Error Handling

### ValueError
Raised when verse or surah not found:

```python
try:
    verse = qal.get_verse(999, 1)  # Invalid surah
except ValueError as e:
    print(f"Error: {e}")

try:
    verse = surah[999]  # Invalid ayah
except ValueError as e:
    print(f"Error: {e}")
```

### Valid Ranges
- **Surah numbers**: 1-114
- **Ayah numbers**: 
  - 0 for Basmala (available in surahs 2-114 except 9)
  - 1+ for regular ayahs (varies by surah)

## Best Practices

### Performance Tips
1. **Use direct access**: `db[surah][ayah]` (fastest)
2. **Cache surah objects**: `surah = qal.get_surah(3); verse = surah[35]`
3. **Use normalized search**: Better matching results
4. **Check existence first**: `if ayah in surah:` before access

### Memory Considerations
1. **Database loads once**: 6,348 verses loaded at import
2. **Efficient storage**: Hashmap-based with minimal overhead
3. **Surah objects are lightweight**: Safe to cache and reuse
Raised when an invalid ayah number is provided for a given surah.

### SearchError

Raised when search operations fail.

## Constants

```python
TOTAL_SURAHS = 114
MIN_SURAH = 1
MAX_SURAH = 114
SUPPORTED_LANGUAGES = ['arabic', 'english']
SUPPORTED_TRANSLATIONS = ['english', 'urdu', 'french']
```

## Usage Examples

### Basic Search

```python
from quran_ayah_lookup import QuranLookup

quran = QuranLookup()

# Search for text
results = quran.search_text("الحمد لله")
for result in results:
    print(f"Found in {result.ayah.surah}:{result.ayah.ayah}")
    print(f"Score: {result.score}")
```

### Error Handling

```python
from quran_ayah_lookup import QuranLookup, InvalidSurahError

quran = QuranLookup()

try:
    ayah = quran.get_ayah(surah=115, ayah=1)  # Invalid surah
except InvalidSurahError as e:
    print(f"Error: {e}")
```

## Performance Notes

- Text searches are optimized using RapidFuzz for fast string matching
- Results are cached to improve repeated query performance
- Large result sets are paginated automatically

## Version Information

Current API version: 0.0.1 (planned)

For the latest API updates, check the [changelog](../CHANGELOG.md).