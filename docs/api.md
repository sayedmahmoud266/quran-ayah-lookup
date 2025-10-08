# API Reference

## Overview

This document provides detailed API reference for the Quran Ayah Lookup package.

*Note: This is the planned API structure. Implementation is pending.*

## Classes

### QuranLookup

Main class for interacting with Quran text and search functionality.

#### Constructor

```python
QuranLookup(language='arabic', translation='english')
```

**Parameters:**
- `language` (str): Primary language for Quran text. Default: 'arabic'
- `translation` (str): Translation language. Default: 'english'

#### Methods

##### search_text()

Search for ayahs containing specific text.

```python
search_text(query, surah_range=None, max_results=100, fuzzy=False)
```

**Parameters:**
- `query` (str): Text to search for
- `surah_range` (tuple, optional): Range of surahs to search (start, end)
- `max_results` (int): Maximum number of results to return
- `fuzzy` (bool): Enable fuzzy matching

**Returns:**
- List of `SearchResult` objects

##### get_ayah()

Retrieve a specific ayah by surah and ayah number.

```python
get_ayah(surah, ayah, include_translation=True)
```

**Parameters:**
- `surah` (int): Surah number (1-114)
- `ayah` (int): Ayah number within the surah
- `include_translation` (bool): Include translation in result

**Returns:**
- `Ayah` object

##### fuzzy_search()

Perform fuzzy text matching.

```python
fuzzy_search(query, threshold=0.7, max_results=50)
```

**Parameters:**
- `query` (str): Text to match against
- `threshold` (float): Minimum similarity score (0.0-1.0)
- `max_results` (int): Maximum results to return

**Returns:**
- List of `FuzzyResult` objects

## Data Classes

### Ayah

Represents a single ayah from the Quran.

**Attributes:**
- `surah` (int): Surah number
- `ayah` (int): Ayah number
- `text` (str): Arabic text
- `translation` (str, optional): Translation text
- `transliteration` (str, optional): Transliterated text

### SearchResult

Result from text search operations.

**Attributes:**
- `ayah` (Ayah): The matching ayah
- `score` (float): Relevance score
- `match_positions` (List[tuple]): Character positions of matches

### FuzzyResult

Result from fuzzy search operations.

**Attributes:**
- `ayah` (Ayah): The matching ayah
- `similarity` (float): Similarity score (0.0-1.0)
- `matched_text` (str): The specific text that matched

## Exceptions

### QuranLookupError

Base exception for all package-related errors.

### InvalidSurahError

Raised when an invalid surah number is provided.

### InvalidAyahError

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