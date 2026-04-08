# Quran Ayah Lookup

[![PyPI version](https://badge.fury.io/py/quran-ayah-lookup.svg)](https://badge.fury.io/py/quran-ayah-lookup)
[![Python Support](https://img.shields.io/pypi/pyversions/quran-ayah-lookup.svg)](https://pypi.org/project/quran-ayah-lookup/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A high-performance Python package for Quranic ayah lookup with **O(1) verse access** and Arabic text normalization. **Arabic only** - translations are not supported at this time.

**Quran Corpus Source**: This package uses the Quran text corpus from [Tanzil.net](https://tanzil.net/), a trusted source for accurate Quranic text.

## Features

- 🚀 **O(1) Performance**: Lightning-fast verse lookup (956x faster than linear search!)
- ⚡ **207x Faster Sliding Window**: New alignment-based algorithm (54ms vs 11s per query!)
- 📖 **Ayah Lookup**: Direct access with `db[surah][ayah]` syntax
- 🔍 **Arabic Text Search**: Search for ayahs using Arabic text
- 🎯 **Fuzzy Search**: Advanced partial text matching with similarity scoring
- 🔄 **Multi-Ayah Search**: Sliding window search for text spanning multiple verses
- 🧠 **Smart Search**: Automatic method selection for optimal results
- 📍 **Contextual Search Hints**: `surah_hint` and `start_after` narrow the initial search window before falling back to the full corpus — available across all search methods, CLI flags, and REST API params
- 📏 **Word-level Positioning**: Precise match locations within verses
- 🎚️ **Smart Basmala Handling**: Automatic Basmala extraction and organization
- 🔤 **Text Normalization**: Advanced Arabic diacritics removal and Alif normalization
- 🏗️ **Chapter-based Structure**: Efficient QuranChapter organization
- 💾 **Performance Cache**: Pre-computed corpus and word lists for optimal speed
- 📊 **Basmalah-Aware Counting**: Precise verse counts with/without Basmalas
- 🎯 **Absolute Indexing**: O(1) access to any verse by absolute position (0-6347)
- 📚 **Multi-Database Cache**: Load multiple text styles simultaneously without eviction
- 🔮 **Semantic Vector Search**: Hybrid semantic+lexical search (e5-base + BM25 + RRF, or MiniLM cosine) via optional `[vector]` extras
- 💻 **CLI Interface**: Command-line tool with interactive REPL mode (`qal` command)
- 🌐 **REST API**: HTTP endpoints with Swagger documentation (`qal serve`)
- 🕌 **Arabic Only**: Focused on Arabic Quranic text (no translations supported)
- 📚 **Tanzil.net Corpus**: Uses trusted Quran text from Tanzil.net
- ✨ **Complete Coverage**: Full Quran with 6,348 verses including Basmalas

## Installation

### From PyPI (Recommended)

```bash
pip install quran-ayah-lookup
```

### From Source

```bash
git clone https://github.com/sayedmahmoud266/quran-ayah-lookup.git
cd quran-ayah-lookup
pip install -e .
```

## Quick Start

### Python API

```python
import quran_ayah_lookup as qal

# Database loads automatically on import
# ✓ Quran database loaded successfully:
#   - Total verses: 6348
#   - Total surahs: 114
#   - Source: Tanzil.net

# O(1) Direct verse access
verse = qal.get_verse(3, 35)  # Surah Al-Imran, Ayah 35
print(verse.text)  # Original Arabic text with diacritics
print(verse.text_normalized)  # Normalized text without diacritics

# Even faster: Direct database access
db = qal.get_quran_database()
verse = db[3][35]  # O(1) lookup!

# Get entire surah/chapter
surah = qal.get_surah(3)  # Al-Imran
basmala = surah[0]        # Basmala (ayah 0)
first_ayah = surah[1]     # First ayah
print(f"Surah has {len(surah)} verses")

# Search Arabic text
results = qal.search_text("الله")
print(f"Found {len(results)} verses containing 'الله'")

# Fuzzy search with partial matching
fuzzy_results = qal.fuzzy_search("كذلك يجتبيك ربك ويعلمك", threshold=0.8)
for result in fuzzy_results[:3]:
    print(f"Surah {result.verse.surah_number}:{result.verse.ayah_number} (similarity: {result.similarity:.3f})")

# Multi-ayah sliding window search (for text spanning multiple verses)
multi_results = qal.search_sliding_window("الرحمن علم القران خلق الانسان علمه البيان", threshold=80.0)
for match in multi_results[:3]:
    print(f"{match.get_reference()}: {match.similarity:.1f}% similarity")

# Smart search (automatically selects best method)
smart_result = qal.smart_search("الرحمن الرحيم")
print(f"Used {smart_result['method']} search, found {smart_result['count']} results")

# Find repeated phrases
repeated = qal.fuzzy_search("فبأي الاء ربكما تكذبان")
print(f"Found {len(repeated)} occurrences of this repeated phrase")

# --- Contextual search hints ---

# surah_hint: search Surah 12 first, expand ±1/±3, then full Quran
results = qal.search_text("يجتبيك", surah_hint=12)

# start_after: only return results after Surah 2, Ayah 255
results = qal.fuzzy_search("الله لا اله الا هو", start_after=(2, 255))

# Combine both hints in smart_search
result = qal.smart_search("علم القران", surah_hint=55, start_after=(54, 55))

# Check verse existence (O(1))
if 35 in surah:
    verse = surah[35]

# Get all verses from a surah
all_verses = surah.get_all_verses()
```

## Quran Text Styles

The package supports **multiple Quran text styles** from [Tanzil.net](https://tanzil.net/), allowing you to choose the text representation that best fits your use case.

### Available Styles

- **`UTHMANI_ALL`** (default) - Full Uthmani script with all tashkeel and harakat (most complete)
- **`UTHMANI`** - Uthmani script with standard diacritics
- **`SIMPLE`** - Simplified text with basic diacritics
- **`SIMPLE_PLAIN`** - Plain simplified text
- **`SIMPLE_CLEAN`** - Cleaned simplified text
- **`SIMPLE_MINIMAL`** - Minimal simplified text (least diacritics)

All corpus files are available in `src/quran_ayah_lookup/resources/`. You can download and compare these versions at [Tanzil.net](https://tanzil.net/download/).

### Switching Between Styles

#### 1. Using Environment Variable

Set the `QAL_STYLE` environment variable (works from shell or `.env` file):

```bash
# From command line
export QAL_STYLE=SIMPLE
qal verse 1 1

# Or directly with the command
QAL_STYLE=SIMPLE qal verse 1 1
```

Create a `.env` file in your project directory:

```env
QAL_STYLE=SIMPLE
```

#### 2. Using CLI Option

Pass the `--style` or `-s` option to any CLI command:

```bash
# Get verse with specific style
qal verse 1 1 --style=SIMPLE
qal verse 1 1 -s SIMPLE

# Search with different style
qal search "الله" --style=UTHMANI

# Works with all commands
qal fuzzy "بسم الله" -s SIMPLE_MINIMAL
qal smart-search "الرحمن الرحيم" --style=SIMPLE_CLEAN
```

#### 3. From Python Library

**Option A: Initialize with specific style**

```python
import quran_ayah_lookup as qal

# Get database with specific style
db = qal.get_quran_database(qal.QuranStyle.SIMPLE)

# Now use the database
verse = db.get_verse(1, 1)
print(verse.text)
```

**Option B: Switch style dynamically**

```python
import quran_ayah_lookup as qal

# Database loads with default style (UTHMANI_ALL)
verse = qal.get_verse(1, 1)

# Switch to a different style
qal.switch_quran_style(qal.QuranStyle.SIMPLE)

# Now all queries use the new style
verse = qal.get_verse(1, 1)
```

**Option C: Disable auto-initialization and control loading**

```python
import quran_ayah_lookup.models as models
import quran_ayah_lookup as qal

# Disable automatic initialization on import
models.default_settings.autoload_on_import = False

# Initialize with your preferred style
qal.initialize_quran_database(qal.QuranStyle.SIMPLE)

# Now use the package
verse = qal.get_verse(1, 1)
```

**Option D: Update default settings directly**

```python
import quran_ayah_lookup as qal

# Change the default style before initialization
qal.default_settings.style = qal.QuranStyle.SIMPLE_CLEAN

# Reinitialize the database
qal.initialize_quran_database()

# Use the package
verse = qal.get_verse(1, 1)
```

**Option E: Load multiple styles simultaneously (new in 0.1.6)**

All loaded databases are cached independently. Loading an additional style never evicts the current default.

```python
import quran_ayah_lookup as qal

# Default database loads with UTHMANI_ALL on import
db_uthmani = qal.get_quran_database()

# Load SIMPLE alongside — UTHMANI_ALL remains cached
db_simple = qal.get_quran_database(qal.QuranStyle.SIMPLE)

# Both databases are live and independent
verse_uthmani = db_uthmani.get_verse(1, 1)
verse_simple  = db_simple.get_verse(1, 1)

print(verse_uthmani.text)  # Full Uthmani script with all tashkeel
print(verse_simple.text)   # Simplified script

# get_quran_database() still returns the original default
assert qal.get_quran_database() is db_uthmani

# switch_quran_style changes the default but keeps the old db in cache
qal.switch_quran_style(qal.QuranStyle.SIMPLE)
assert qal.get_quran_database() is db_simple          # new default
assert qal.get_quran_database(qal.QuranStyle.UTHMANI_ALL) is db_uthmani  # still cached
```

### Command Line Interface (CLI)

The package includes a powerful CLI accessible via `quran-ayah-lookup` or `qal` for quick lookups and searches:

#### Get a Specific Verse

```bash
# Get verse 35 from Surah 3 (Al-Imran)
qal verse 3 35

# Show only normalized text
qal verse 3 35 --normalized

# Show only original text with diacritics
qal verse 3 35 --original
```

#### Get Surah Information

```bash
# Show surah information
qal surah 3

# Show verse count only
qal surah 3 --count

# List all verses in the surah
qal surah 3 --list
```

#### Search for Text

```bash
# Search for verses containing "الله"
qal search "الله"

# Limit results to 5
qal search "الله" --limit 5

# Search in original text (with diacritics)
qal search "بِسْمِ" --original

# Restrict search to Surah 2 first, then expand
qal search "الله" --surah-hint 2

# Search only after Surah 2:255
qal search "الله" --start-after 2:255
```

#### Fuzzy Search

```bash
# Fuzzy search with default threshold (0.7)
qal fuzzy "كذلك يجتبيك ربك ويعلمك"

# Use custom similarity threshold
qal fuzzy "بسم الله" --threshold 0.9

# Limit fuzzy search results
qal fuzzy "الله" --limit 10

# Restrict to a surah before expanding to full Quran
qal fuzzy "الرحمن" --surah-hint 55

# Start after a specific position
qal fuzzy "الله" --start-after 2:255
```

#### Sliding Window Search (Multi-Ayah)

```bash
# Search for text spanning multiple ayahs
qal sliding-window "الرحمن علم القران خلق الانسان علمه البيان"

# Use custom similarity threshold (0.0-100.0)
qal sliding-window "بسم الله الرحمن الرحيم الحمد لله" --threshold 85.0

# Limit results
qal sliding-window "الرحمن علم القران" --limit 5

# Hint to search in Surah 55 first
qal sliding-window "الرحمن علم القران" --surah-hint 55

# Start after a specific position
qal sliding-window "الله" --start-after 54:55
```

#### Smart Search (Automatic Method Selection)

```bash
# Let the package choose the best search method
qal smart-search "الرحمن الرحيم"

# Configure thresholds for each method
qal smart-search "الحمد لله" --fuzzy-threshold 0.8 --sliding-threshold 85.0

# Limit results
qal smart-search "بسم الله" --limit 10

# With contextual hints
qal smart-search "علم القران" --surah-hint 55
qal smart-search "الله" --start-after 2:255
```

#### List All Verses in a Surah

```bash
# List all verses in Surah 1 (Al-Fatiha)
qal list-verses 1

# List all verses in Surah 114 (An-Nas)
qal list-verses 114
```

#### Show Database Statistics

```bash
# Display Quran database statistics
qal stats
```

#### Interactive REPL Mode

Start an interactive Read-Eval-Print Loop session by running the command without any arguments:

```bash
# Start interactive REPL mode
qal

# Or use the full command
quran-ayah-lookup
```

In REPL mode, you can run commands interactively:

```
============================================================
Quran Ayah Lookup - Interactive REPL Mode
============================================================
Commands:
  verse <surah> <ayah>       - Get a specific verse
  surah <number>             - Get surah information
  search <query>             - Search for text
  fuzzy <query>              - Fuzzy search
  sliding-window <query>     - Multi-ayah sliding window search
  smart-search <query>       - Smart search (auto-selects method)
  stats                      - Show database stats
  help                       - Show this help
  exit / quit / Ctrl+C       - Exit REPL
============================================================

qal> verse 1 1
Ayah 1:1
----------------------------------------
Original: بِسۡمِ ٱللَّهِ ٱلرَّحۡمَٰنِ ٱلرَّحِيمِ
Normalized: بسم الله الرحمن الرحيم

qal> search الله
Found 2851 verse(s)

qal> stats
Total surahs: 114
Total verses: 6348

qal> exit
Goodbye!
```

#### Get Help

```bash
# Show all available commands
qal --help

# Show help for a specific command
qal verse --help
qal search --help
qal fuzzy --help

# Show version
qal --version
```

## Performance & Advanced Features

### ⚡ High-Performance Sliding Window Search

The new alignment-based sliding window algorithm delivers **207x faster** performance compared to the previous implementation:

```python
import quran_ayah_lookup as qal

# Load database (cache is enabled by default)
db = qal.load_quran_db()

# Multi-ayah search - now 207x faster!
query = "الرحمن علم القران خلق الانسان علمه البيان"
results = qal.search_sliding_window(query, threshold=80.0, max_results=5, db=db)

for result in results:
    print(f"Match: Surah {result.surah_start}:{result.ayah_start} to {result.surah_end}:{result.ayah_end}")
    print(f"Similarity: {result.similarity:.1f}%")
    print(f"Matched text: {result.matched_text[:100]}...")
    print()
```

**Performance Results:**

- **Old Algorithm**: ~11,150ms per query (11.15 seconds)
- **New Algorithm**: ~54ms per query
- **Speedup**: 207x faster! 🚀

### 💾 Performance Cache System

The cache system pre-computes corpus data for optimal speed:

```python
import quran_ayah_lookup as qal

# Cache is enabled by default
db = qal.load_quran_db()  # Cache is built automatically

# Disable cache if needed (for minimal memory footprint)
qal.__enable_cache__ = False
db = qal.load_quran_db()  # No cache, uses ~28% less memory

# Re-enable cache
qal.__enable_cache__ = True
db = qal.load_quran_db()
```

**Cache Performance Benefits:**

- **With Cache**: ~54ms average per sliding window query
- **Without Cache**: ~69ms average per sliding window query
- **Speedup**: ~28% faster with cache enabled

**What's Cached:**

- Full combined corpus text (720,944 chars original, 405,394 normalized)
- Pre-split word lists (82,459 original words, 77,881 normalized)
- Pre-sorted reference lists (114 surahs, 6,348 ayah tuples)
- Character-to-word offset mappings for O(log n) lookups

### 📊 Basmalah-Aware Counting

Get accurate verse counts with or without Basmalas:

```python
import quran_ayah_lookup as qal

db = qal.load_quran_db()

# Total verses including Basmalas (default)
total_with_basmalah = db.get_verse_count(include_basmalah=True)
print(f"Total verses with Basmalah: {total_with_basmalah}")  # 6,348

# Total verses without Basmalas
total_without_basmalah = db.get_verse_count(include_basmalah=False)
print(f"Total verses without Basmalah: {total_without_basmalah}")  # 6,236

# Get all verses (includes Basmalas)
all_verses = db.get_all_verses()
print(f"Retrieved {len(all_verses)} verses")  # 6,348

# Check if a surah has a Basmala
surah = db.get_surah(1)
if surah.has_basmala():
    print(f"Surah {surah.number} has a Basmala")
```

**Key Facts:**

- Total Quranic verses: **6,236** (without Basmalas)
- Total with Basmalas: **6,348** (112 Basmalas for surahs 2-114, except At-Tawbah)
- Surah 1 (Al-Fatiha): Basmala is verse 1:1
- Surah 9 (At-Tawbah): No Basmala
- Surahs 2-114 (except 9): Basmala stored separately with ayah=0

### 🎯 Absolute Indexing

Access any verse by its absolute position (0-6347):

```python
import quran_ayah_lookup as qal

db = qal.load_quran_db()

# Get verse by absolute index (O(1) lookup)
verse = db.get_verse_by_absolute_index(0)  # First verse: 1:1
print(f"Verse {verse.surah}:{verse.ayah}: {verse.text_normalized}")

verse = db.get_verse_by_absolute_index(6347)  # Last verse: 114:6
print(f"Verse {verse.surah}:{verse.ayah}: {verse.text_normalized}")

# Convert between absolute and (surah, ayah) coordinates
absolute_idx = db.verse_to_absolute_index(1, 1)  # Returns 0
print(f"Verse 1:1 is at absolute index {absolute_idx}")

surah, ayah = db.absolute_index_to_verse(0)  # Returns (1, 1)
print(f"Absolute index 0 is verse {surah}:{ayah}")
```

### 🔍 Smart Search (Automatic Method Selection)

Let the package automatically choose the best search method:

```python
import quran_ayah_lookup as qal

db = qal.load_quran_db()

# Smart search automatically selects:
# - Exact search for short queries (< 10 chars)
# - Fuzzy search for medium queries (10-50 chars)
# - Sliding window for long queries (> 50 chars)
result = qal.smart_search("الرحمن الرحيم", db=db)

print(f"Used {result['method']} search")
print(f"Found {len(result['results'])} result(s)")
```

## REST API

The package includes a REST API server that exposes all functionalities via HTTP endpoints with automatic Swagger documentation.

### Starting the API Server

```bash
# Start server (default: http://127.0.0.1:8000)
qal serve

# Custom host and port
qal serve --host 0.0.0.0 --port 8080

# Development mode with auto-reload
qal serve --reload
```

### Installation

Install with API support:

```bash
pip install "quran-ayah-lookup[api]"
```

Or install dependencies separately:

```bash
pip install fastapi uvicorn[standard]
```

### API Documentation

Once the server is running, access the interactive documentation:

- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

### Available Endpoints

- `GET /verses/{surah}/{ayah}` - Get a specific verse
- `GET /surahs/{surah}` - Get surah information
- `GET /surahs/{surah}/verses` - Get all verses in a surah
- `GET /search?query={text}&surah_hint={n}&start_after_surah={n}&start_after_ayah={n}` - Search for verses
- `GET /fuzzy-search?query={text}&threshold={0.7}&surah_hint={n}&start_after_surah={n}&start_after_ayah={n}` - Fuzzy search
- `GET /sliding-window?query={text}&threshold={80.0}&surah_hint={n}&start_after_surah={n}&start_after_ayah={n}` - Multi-ayah sliding window search
- `GET /smart-search?query={text}&surah_hint={n}&start_after_surah={n}&start_after_ayah={n}` - Smart search (auto-selects method)
- `GET /vector-search?query={text}&asymmetric=true&semantic_only=false` - Semantic vector search (requires `[vector]` extras)
- `GET /stats` - Database statistics
- `GET /health` - Health check

> **Note**: `start_after_surah` and `start_after_ayah` must always be provided together — passing only one returns HTTP 400.

### Quick API Example

```bash
# Get a verse
curl http://127.0.0.1:8000/verses/1/1

# Search (URL-encoded)
curl "http://127.0.0.1:8000/search?query=%D8%A7%D9%84%D9%84%D9%87&limit=5"

# Fuzzy search
curl "http://127.0.0.1:8000/fuzzy-search?query=%D8%A8%D8%B3%D9%85%20%D8%A7%D9%84%D9%84%D9%87&threshold=0.8"

# Sliding window search
curl "http://127.0.0.1:8000/sliding-window?query=%D8%A7%D9%84%D8%B1%D8%AD%D9%85%D9%86%20%D8%B9%D9%84%D9%85%20%D8%A7%D9%84%D9%82%D8%B1%D8%A7%D9%86&threshold=80.0"

# Smart search
curl "http://127.0.0.1:8000/smart-search?query=%D8%A7%D9%84%D8%B1%D8%AD%D9%85%D9%86%20%D8%A7%D9%84%D8%B1%D8%AD%D9%8A%D9%85"

# Get stats
curl http://127.0.0.1:8000/stats
```

Using Python:

```python
import requests

# Get verse
response = requests.get("http://127.0.0.1:8000/verses/1/1")
verse = response.json()

# Search
response = requests.get("http://127.0.0.1:8000/search",
                       params={"query": "الله", "limit": 5})
results = response.json()

# Fuzzy search
response = requests.get("http://127.0.0.1:8000/fuzzy-search",
                       params={"query": "بسم الله", "threshold": 0.8})
fuzzy_results = response.json()

# Sliding window search
response = requests.get("http://127.0.0.1:8000/sliding-window",
                       params={"query": "الرحمن علم القران", "threshold": 80.0})
sliding_results = response.json()

# Smart search
response = requests.get("http://127.0.0.1:8000/smart-search",
                       params={"query": "الرحمن الرحيم"})
smart_result = response.json()
print(f"Used {smart_result['method']} search")
```

For complete API documentation, see [docs/api.md](docs/api.md#rest-api-reference).

## Semantic Vector Search

Hybrid semantic search powered by sentence-transformers and FAISS. Requires the optional `[vector]` extras.

### Installation

```bash
pip install "quran-ayah-lookup[vector]"
make build-vector-index   # builds all 5 index artefacts in resources/vector/
```

### Retrieval Modes

| Mode | Model | Method | Best for |
|------|-------|--------|----------|
| **Asymmetric** (default) | `intfloat/multilingual-e5-base` (768-dim) | FAISS cosine + BM25Okapi fused via RRF (k=60) | General queries, mixed Arabic/meaning |
| **Symmetric** | `paraphrase-multilingual-MiniLM-L12-v2` (384-dim) | FAISS cosine only | Paraphrase / meaning-only queries |

The `semantic_only=True` flag disables BM25+RRF in asymmetric mode and uses pure FAISS cosine ranking.

### Python Library

```python
from quran_ayah_lookup.vector_search import VectorSearch

vs = VectorSearch()

# Default: asymmetric (e5-base + BM25 + RRF)
result = vs.vector_search("الرحمن علم القران", threshold=0.7)

# Symmetric mode (MiniLM, FAISS only)
result = vs.vector_search("mercy and compassion", asymmetric=False)

# Pure FAISS cosine — no BM25 or RRF
result = vs.vector_search("آية الكرسي", semantic_only=True)

# Restrict to a surah (expands ±1, ±2, … if no confident match found)
result = vs.vector_search("وما خلقت", surah_hint=51, threshold=0.75)

# Boost verses that appear after a given position
result = vs.vector_search("يا أيها الناس", start_after=(2, 100))

print(result.get_reference())   # e.g. "2:255"
print(result.matched_text)
```

### CLI

```bash
# Default asymmetric search
qal vector-search "الرحمن علم القران"

# Symmetric mode
qal vector-search "mercy and compassion" --symmetric

# Pure FAISS cosine (skip BM25+RRF)
qal vector-search "آية الكرسي" --semantic-only

# Restrict to Surah 2, custom threshold
qal vector-search "الله لا إله إلا هو" --surah-hint 2 --threshold 0.8

# Start-after positional hint
qal vector-search "يا أيها الناس" --start-after 2:100

# Normalize query before search
qal vector-search "بسم الله الرحمن الرحيم" --normalize
```

### REST API

```bash
# Default asymmetric
curl "http://127.0.0.1:8000/vector-search?query=الرحمن%20علم%20القران"

# Symmetric mode
curl "http://127.0.0.1:8000/vector-search?query=mercy&asymmetric=false"

# Semantic-only (no BM25)
curl "http://127.0.0.1:8000/vector-search?query=آية%20الكرسي&semantic_only=true"

# With surah hint and threshold
curl "http://127.0.0.1:8000/vector-search?query=الله%20لا%20إله%20إلا%20هو&surah_hint=2&threshold=0.8"
```

Returns the same `MultiAyahMatch` response model as `/sliding-window`. Returns `503` if `[vector]` extras are not installed or the index has not been built.

### Advanced Features

- **Partial ayah detection**: `start_word`/`end_word` fields indicate which words matched within a verse
- **Sequence detection**: queries longer than 1.3× the matched verse automatically append the next 1–3 consecutive verses
- **Positional gravity**: `start_after` applies a 15 % RRF score boost to later verses (ranking-only, does not affect reported similarity)
- **Expanding surah window**: `surah_hint` first searches only that surah, then expands ±1, ±2, … until a confident result is found

## Performance

### Search Performance Benchmarks

**Sliding Window Search (Multi-Ayah):**

- **Old Algorithm**: ~11,150ms per query (11.15 seconds)
- **New Algorithm**: ~54ms per query
- **Speedup**: 207x faster! 🚀

**Cache Impact:**

- **With Cache**: ~54ms average (recommended)
- **Without Cache**: ~69ms average
- **Cache Speedup**: ~28% faster

### O(1) Lookup Performance

```
O(1) lookup (1000x): 0.0006s
O(n) lookup (1000x): 0.5725s
Speedup: 956x faster! 🚀
```

### Database Structure

- **6,348 total verses** (6,236 original + 112 Basmalas)
- **114 surahs** with chapter-based organization
- **Hashmap-based storage** for O(1) access
- **Smart Basmala handling** for surahs 2-114 (except At-Tawbah)
- **Pre-computed cache** for optimal sliding window performance

## API Reference

### Core Functions

```python
# Verse lookup
verse = qal.get_verse(surah_number, ayah_number)
db[surah_number][ayah_number]  # Direct O(1) access

# Surah/Chapter access
surah = qal.get_surah(surah_number)
surah[ayah_number]  # O(1) verse access
len(surah)  # Verse count
surah.has_basmala()  # Check for Basmala

# Search and utility
results = qal.search_text(query, normalized=True, surah_hint=None, start_after=None)
fuzzy_results = qal.fuzzy_search(query, threshold=0.7, max_results=10, surah_hint=None, start_after=None)
sliding_results = qal.search_sliding_window(query, threshold=80.0, max_results=None, surah_hint=None, start_after=None)
smart_result = qal.smart_search(query, threshold=0.7, sliding_threshold=80.0, surah_hint=None, start_after=None)
verses = qal.get_surah_verses(surah_number)
normalized = qal.normalize_arabic_text(text)
```

**Contextual hint parameters (all search functions):**
- `surah_hint` (int, optional): Search in this surah first; expands ±1, ±3 surahs, then full Quran. Fallback results sorted by proximity to the hint.
- `start_after` (tuple, optional): `(surah, ayah)` position; only searches verses after this point. Falls back to full Quran if nothing found, prioritising later matches.

### Data Models

- **`QuranVerse`**: Individual verse with original and normalized text
- **`QuranChapter`**: Surah container with O(1) verse access
- **`QuranDatabase`**: Main database with chapter organization
- **`FuzzySearchResult`**: Fuzzy search result with similarity and position data

## Requirements

### Core Requirements

- Python 3.8 or higher
- rapidfuzz >= 3.0.0
- click >= 8.0.0

### Optional (for REST API)

- fastapi >= 0.104.0
- uvicorn[standard] >= 0.24.0

Install with: `pip install "quran-ayah-lookup[api]"`

### Optional (for Semantic Vector Search)

- sentence-transformers
- faiss-cpu
- rank-bm25

Install with: `pip install "quran-ayah-lookup[vector]"` then build the index: `make build-vector-index`

## Development

### Setting up Development Environment

1. Clone the repository:

```bash
git clone https://github.com/sayedmahmoud266/quran-ayah-lookup.git
cd quran-ayah-lookup
```

2. Initialize development environment:

```bash
make init                # Initialize virtual environment
make install-deps        # Install production dependencies
make install-deps-dev    # Install development dependencies
```

3. Run tests:

```bash
make test                # Run unit tests
make test-coverage       # Run tests with coverage report
```

### Available Make Commands

Use `make help` to see all available commands:

```bash
make help               # Show all available commands
make init               # Initialize virtual environment
make install-deps       # Install production dependencies
make install-deps-dev   # Install development dependencies
make install-dev        # Install package in development mode
make test               # Run unit tests
make test-coverage      # Run tests with coverage report
make format             # Format code with black
make lint               # Lint code with flake8
make typecheck          # Type check with mypy
make check              # Run all checks (format, lint, typecheck, test)
make build              # Build the package
make clean              # Clean build artifacts
make clean-all          # Clean everything including virtual environment
make build-vector-index # Build FAISS + BM25 vector search indexes (requires [vector] extras)
make setup-dev          # Complete development setup (init + install-deps-dev)
make publish-test       # Publish to test PyPI
make publish            # Publish to PyPI
```

### Quick Development Setup

For a complete development environment setup:

```bash
make setup-dev          # Does: init + install-deps-dev
```

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for your changes
5. Ensure all tests pass (`pytest`)
6. Format your code (`black src/`)
7. Commit your changes (`git commit -m 'Add amazing feature'`)
8. Push to the branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

- **Sayed Mahmoud** - [sayedmahmoud266](https://github.com/sayedmahmoud266)
- Email: foss-support@sayedmahmoud266.website

## Roadmap

### ✅ Completed

- [x] **O(1) Verse Lookup**: Lightning-fast `db[surah][ayah]` access
- [x] **Arabic Text Search**: Full-text search across all verses
- [x] **Fuzzy Matching**: Partial text matching with similarity scoring
- [x] **Sliding Window Search**: Multi-ayah search with 207x performance improvement
- [x] **Smart Basmala Handling**: Automatic extraction and organization
- [x] **Basmalah-Aware Counting**: Precise verse counts with/without Basmalas
- [x] **Text Normalization**: Advanced Arabic diacritics removal
- [x] **Chapter Organization**: Efficient QuranChapter structure
- [x] **Complete Database**: 6,348 verses with proper indexing
- [x] **CLI Interface**: Full-featured command-line tool with REPL mode
- [x] **REST API**: HTTP endpoints with Swagger documentation
- [x] **Performance Cache**: Pre-computed corpus for optimal speed (28% faster)
- [x] **Absolute Indexing**: O(1) access to any verse by position
- [x] **Smart Search**: Automatic method selection based on query length
- [x] **Multiple Text Styles**: 6 Quran text styles from Tanzil.net
- [x] **Multi-Database Cache**: Load multiple styles simultaneously without eviction
- [x] **Semantic Vector Search**: Hybrid semantic+lexical search with dual retrieval modes (asymmetric e5-base+BM25+RRF / symmetric MiniLM FAISS)
- [x] **Contextual Search Hints**: `surah_hint` and `start_after` for all non-vector search methods (library, CLI, REST API)

### 📋 Features To Research In The Future

- [ ] Advanced search filters (surah range, verse types, date ranges)
- [ ] Query result caching and pagination
- [ ] Export functionality (JSON, CSV, Excel)
- [ ] Enhanced documentation with tutorials
- [ ] Translation support (multiple languages)
- [ ] Tafsir (commentary) support
- [ ] Web UI dashboard

## Support

If you encounter any issues or have questions, please:

1. Check the [documentation](docs/)
2. Search existing [issues](https://github.com/sayedmahmoud266/quran-ayah-lookup/issues)
3. Create a [new issue](https://github.com/sayedmahmoud266/quran-ayah-lookup/issues/new) if needed

## Acknowledgments

- **Tanzil.net**: For providing the accurate and trusted Quran text corpus
- Thanks to all contributors who help improve this package
- Special thanks to the maintainers of the RapidFuzz library
- Inspired by the need for accessible Arabic Quranic text search tools

---

_May this tool be beneficial for those seeking to engage with the Quran._ 🤲
