# Quick Start Guide

## Basic Usage

Here's how to get started with the Quran Ayah Lookup package:

```python
from quran_ayah_lookup import QuranLookup

# Initialize the lookup engine
quran = QuranLookup()

print(f"Package version: {quran.__version__}")
```

## Planned Features

*Note: The following features are planned for future releases and are not yet implemented.*

### Text Search

```python
# Search for ayahs containing specific text
results = quran.search_text("بسم الله الرحمن الرحيم")
for result in results:
    print(f"Surah {result.surah}, Ayah {result.ayah}: {result.text}")
```

### Ayah Lookup by Reference

```python
# Get a specific ayah by surah and ayah number
ayah = quran.get_ayah(surah=1, ayah=1)
print(f"Text: {ayah.text}")
print(f"Translation: {ayah.translation}")
```

### Fuzzy Text Search

```python
# Find similar text matches
results = quran.fuzzy_search("الحمد لله رب العالمين", threshold=0.8)
for result in results:
    print(f"Match: {result.text} (Score: {result.score})")
```

### Advanced Search Options

```python
# Search with filters and options
results = quran.search_text(
    query="الصلاة",
    surah_range=(1, 114),  # Search in all surahs
    max_results=10,
    include_translation=True
)
```

## Next Steps

1. Check out the [API Reference](api.md) for detailed documentation
2. Read the [Contributing Guidelines](../CONTRIBUTING.md) if you want to contribute
3. Browse the source code on [GitHub](https://github.com/sayedmahmoud266/quran-ayah-lookup)