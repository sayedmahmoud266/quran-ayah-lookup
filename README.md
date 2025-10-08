# Quran Ayah Lookup

[![PyPI version](https://badge.fury.io/py/quran-ayah-lookup.svg)](https://badge.fury.io/py/quran-ayah-lookup)
[![Python Support](https://img.shields.io/pypi/pyversions/quran-ayah-lookup.svg)](https://pypi.org/project/quran-ayah-lookup/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python package for looking up Quranic ayahs by their number or Arabic text. **Arabic only** - translations are not supported at this time.

**Quran Corpus Source**: This package uses the Quran text corpus from [Tanzil.net](https://tanzil.net/), a trusted source for accurate Quranic text.

## Features

- 🔍 **Arabic Text Search**: Search for ayahs using partial or complete Arabic text
- 📖 **Ayah Lookup**: Find specific ayahs by surah and ayah number
- ⚡ **Fast Matching**: Powered by RapidFuzz for efficient fuzzy text matching
- 🕌 **Arabic Only**: Focused on Arabic Quranic text (no translations supported)
- 📚 **Tanzil.net Corpus**: Uses trusted Quran text from Tanzil.net
- 🎯 **Complete Coverage**: Full Quran text database

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
from quran_ayah_lookup import QuranLookup

# Initialize the lookup engine
quran = QuranLookup()

# Search by text (implementation coming soon)
# results = quran.search_text("بسم الله الرحمن الرحيم")

# Lookup by surah and ayah number (implementation coming soon)
# ayah = quran.get_ayah(surah=1, ayah=1)

print("Package initialized successfully!")
print(f"Version: {quran.__version__}")
```

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
make install:deps        # Install production dependencies
make install:deps:dev    # Install development dependencies
```

3. Run tests:
```bash
make test
```

4. Format code:
```bash
black src/
```

5. Type checking:
```bash
mypy src/
```

### Building the Package

```bash
python -m build
```

### Publishing to PyPI

```bash
python -m twine upload dist/*
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

- [ ] Implement Arabic text search functionality
- [ ] Add ayah lookup by reference
- [ ] Add fuzzy matching for Arabic text searches
- [ ] Implement caching for improved performance
- [ ] Add CLI interface
- [ ] Web API endpoint support
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