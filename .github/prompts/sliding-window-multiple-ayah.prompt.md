---
mode: agent
---

# Role
You are a highly skilled software developer with expertise in Python programming.

# Task
Your task is to add one more search function to the existing library in the file `__init__.py`. This function should allow users to search for Quranic verses using a sliding window approach that can match multiple ayahs based on a given text input. The function should return a list of verses that match the input text, considering variations in spacing and punctuation.


# Core Logic
1. The function should accept a string input representing the text to search for, and an optional threshold parameter for fuzzy matching (default to 80).
2. It should normalize the input text by removing diacritics and normalizing characters (e.g., normalizing Alif variations).
3. Implement a sliding window algorithm that scans through the verses in the Quran database, concatenating all verses into a single text stream, and then sliding a window of text across this stream.
4. Each window should be of a size that can accommodate the length of the normalized input text.
5. For each window of text, compare it to the normalized input text using fuzzy matching (e.g., using the `rapidfuzz` library).
6. use the following example for vectorized fuzzy searching:
```python
from rapidfuzz import process, fuzz
import numpy as np

# Example setup
paragraphs = [p.strip() for p in open("large_text.txt").read().split("\n\n") if p.strip()]
query = "sample fuzzy text"

# Compute similarity for all paragraphs at once
scores = process.cdist([query], paragraphs, scorer=fuzz.partial_ratio)[0]

# Convert to NumPy for convenience
scores = np.array(scores)

# Get top matches
threshold = 80
indices = np.where(scores >= threshold)[0]
sorted_idx = indices[np.argsort(-scores[indices])]

for i in sorted_idx:
    score = scores[i]
    match = paragraphs[i]
    print(f"[{score:.1f}] {match[:80]}...")
```
7. Return a list of verses that meet a certain similarity threshold (e.g., 80%).
8. Also must specify the start and end word indices of the matched text, either within a single ayah or spanning multiple ayahs.
9. Ensure the function is well-documented with docstrings explaining its purpose, parameters, and return values.
10. Add the newly created function the `cli.py` file and to the `api.py` file to expose it via the CLI and REST API respectively.
11. Create unit tests for this function in the `tests` directory to ensure its correctness and robustness.
12. Here are a few test cases to consider:
    - query: "الرحمن علم القران خلق الانسان علمه البيان" (exact match spanning multiple ayahs) -> should return Surah Ar-Rahman (55:1-4)
    - query: "بسم الله الرحمن الرحيم الم ذلك الكتاب لا ريب فيه هدى للمتقين" (exact match spanning multiple ayahs) -> should return Surah Al-Baqarah (2:1-2)
    - query: "الم يجدك يتيما فاوى ووجدك ضالا فهدى ووجدك عائلا فاغنى فاما اليتيم فلا تقهر واما السائل فلا تنهر و اما بنعمة ربك فحدث بسم الله الرحمن الرحيم الم نشرح لك صدرك (exact match spanning multiple ayahs and surahs) -> should return Surah Ad-Duha (93:6-11) and Surah Ash-Sharh (94:0-1)

# Constraints
- The function must be efficient and capable of handling the entire Quran database without significant performance degradation.
- Do not modify or remove any of the existing functions or classes in the `__init__.py` file, except for adding the new function.
- Ensure that the new function adheres to the coding style and conventions used in the existing codebase.
