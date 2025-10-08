# Quick Start Guide

## Basic Usage

The Quran database loads automatically when you import the package:

```python
import quran_ayah_lookup as qal

# Database loads automatically on import
# ✓ Quran database loaded successfully:
#   - Total verses: 6348  
#   - Total surahs: 114
#   - Source: Tanzil.net
```

## O(1) Verse Lookup

### Direct Database Access (Fastest)

```python
# Get database instance
db = qal.get_quran_database()

# O(1) direct access: db[surah][ayah]
verse = db[3][35]  # Surah Al-Imran, Ayah 35
print(verse.text)  # Original Arabic with diacritics
print(verse.text_normalized)  # Normalized Arabic without diacritics
```

### Using Convenience Functions

```python
# Alternative syntax (also O(1))
verse = qal.get_verse(3, 35)  # Surah 3, Ayah 35
print(f"Surah: {verse.surah_number}, Ayah: {verse.ayah_number}")
print(f"Is Basmala: {verse.is_basmalah}")
```

## Working with Surahs/Chapters

### Get Entire Surah

```python
# Get a surah/chapter with O(1) verse access
surah = qal.get_surah(3)  # Al-Imran
print(f"Surah {surah.number} has {len(surah)} verses")

# Access verses within surah (O(1))
basmala = surah[0]        # Basmala (ayah 0)
first_ayah = surah[1]     # First regular ayah
verse_35 = surah[35]      # Any specific ayah

# Check if verse exists (O(1))
if 35 in surah:
    verse = surah[35]
    
# Get all verses as a list
all_verses = surah.get_all_verses()
print(f"Retrieved {len(all_verses)} verses")
```

### Surah Information

```python
surah = qal.get_surah(2)  # Al-Baqarah
print(f"Has Basmala: {surah.has_basmala()}")
print(f"Verse count: {surah.get_verse_count()}")

# At-Tawbah (special case - no Basmala)
tawbah = qal.get_surah(9)
print(f"At-Tawbah has Basmala: {tawbah.has_basmala()}")  # False
```

## Text Search

### Basic Arabic Text Search

```python
# Search across all verses
results = qal.search_text("الله")
print(f"Found {len(results)} verses containing 'الله'")

for verse in results[:5]:  # Show first 5 results
    print(f"Surah {verse.surah_number}:{verse.ayah_number} - {verse.text[:50]}...")
```

### Normalized vs Original Text Search

```python
# Search in normalized text (recommended - default)
results = qal.search_text("الله", normalized=True)

# Search in original text with diacritics
results = qal.search_text("ٱللَّهِ", normalized=False)
```

## Text Normalization

### Arabic Text Processing

```python
# Normalize Arabic text (remove diacritics, normalize Alif)
original = "بِسْمِ ٱللَّهِ ٱلرَّحْمَـٰنِ ٱلرَّحِيمِ"
normalized = qal.normalize_arabic_text(original)
print(normalized)  # "بسم الله الرحمن الرحيم"
```

## Performance Examples

### Speed Comparison

```python
import time

# O(1) lookup timing
start = time.time()
for i in range(1000):
    verse = db[2][255]  # Al-Baqarah, Ayat al-Kursi
o1_time = time.time() - start

print(f"O(1) lookup (1000x): {o1_time:.4f}s")
# Result: ~0.0006s (956x faster than linear search!)
```

## Common Patterns

### Batch Operations

```python
# Get multiple verses efficiently
verses_to_fetch = [(1, 1), (2, 255), (3, 35), (9, 1)]
verses = [db[s][a] for s, a in verses_to_fetch]

# Process surah by surah
for surah_num in [1, 2, 3]:
    surah = qal.get_surah(surah_num)
    print(f"Processing {len(surah)} verses from surah {surah_num}")
```

### Error Handling

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

## Next Steps

1. Check out the [API Reference](api.md) for detailed documentation
2. Read the [Contributing Guidelines](../CONTRIBUTING.md) if you want to contribute
3. Browse the source code on [GitHub](https://github.com/sayedmahmoud266/quran-ayah-lookup)