# Quran Ayah Lookup

[![PyPI version](https://badge.fury.io/py/quran-ayah-lookup.svg)](https://badge.fury.io/py/quran-ayah-lookup)
[![Python Support](https://img.shields.io/pypi/pyversions/quran-ayah-lookup.svg)](https://pypi.org/project/quran-ayah-lookup/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A high-performance Python package for Quranic ayah lookup with **O(1) verse access** and Arabic text normalization. **Arabic only** - translations are not supported at this time.

**Quran Corpus Source**: This package uses the Quran text corpus from [Tanzil.net](https://tanzil.net/), a trusted source for accurate Quranic text.

## Features

- 🚀 **O(1) Performance**: Lightning-fast verse lookup (956x faster than linear search!)
- 📖 **Ayah Lookup**: Direct access with `db[surah][ayah]` syntax
- 🔍 **Arabic Text Search**: Search for ayahs using Arabic text
- 🎯 **Fuzzy Search**: Advanced partial text matching with similarity scoring
- 🔄 **Repeated Phrases**: Find all occurrences of repeated Quranic phrases
- 📏 **Word-level Positioning**: Precise match locations within verses
- 🎚️ **Smart Basmala Handling**: Automatic Basmala extraction and organization
- 🔤 **Text Normalization**: Advanced Arabic diacritics removal and Alif normalization
- 🏗️ **Chapter-based Structure**: Efficient QuranChapter organization
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

# Find repeated phrases
repeated = qal.fuzzy_search("فبأي الاء ربكما تكذبان")
print(f"Found {len(repeated)} occurrences of this repeated phrase")

# Check verse existence (O(1))
if 35 in surah:
    verse = surah[35]

# Get all verses from a surah
all_verses = surah.get_all_verses()
```

## Performance

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
results = qal.search_text(query, normalized=True)
fuzzy_results = qal.fuzzy_search(query, threshold=0.7, max_results=10)
verses = qal.get_surah_verses(surah_number)
normalized = qal.normalize_arabic_text(text)
```

### Data Models

- **`QuranVerse`**: Individual verse with original and normalized text
- **`QuranChapter`**: Surah container with O(1) verse access
- **`QuranDatabase`**: Main database with chapter organization
- **`FuzzySearchResult`**: Fuzzy search result with similarity and position data

## Requirements

- Python 3.8 or higher
- rapidfuzz >= 3.0.0

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
- [x] **Fuzzy matching for Arabic text searches**: Partial text matching with similarity scoring
- [x] **Smart Basmala Handling**: Automatic extraction and organization
- [x] **Text Normalization**: Advanced Arabic diacritics removal
- [x] **Chapter Organization**: Efficient QuranChapter structure
- [x] **Complete Database**: 6,348 verses with proper indexing

### 🚧 In Progress
- [ ] Advanced search with filters (surah range, verse types)
- [ ] Performance optimizations and caching

### 📋 Planned
- [ ] CLI interface for command-line usage
- [ ] Web API endpoint support
- [ ] Export functionality (JSON, CSV)
- [ ] Enhanced documentation and examples
- [ ] Future: Consider translation support (not currently planned)

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

*May this tool be beneficial for those seeking to engage with the Quran.* 🤲