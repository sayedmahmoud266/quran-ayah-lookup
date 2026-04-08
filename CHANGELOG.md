# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **🎯 Contextual Search Hints** (`surah_hint` and `start_after` parameters): All non-vector search methods now accept two optional positional-hint parameters that guide where to look before falling back to a full-corpus scan.

  - **`surah_hint: int`** — restricts the initial search to the given surah (1-114). If nothing meets the threshold it expands the window ±1, then ±3 surahs, and finally falls back to the entire Quran. Any fallback results are re-sorted so verses nearer the hinted surah appear first.
  - **`start_after: tuple[int, int]`** — accepts a `(surah, ayah)` pair and searches only verses that appear after that position. On failure it falls back to the full Quran and prioritises matches that appear later in the text.
  - Applies to all four search methods: `search_text`, `fuzzy_search`, `search_sliding_window`, and `smart_search` (which propagates the hints through its internal cascade).
  - Both parameters are fully **backward-compatible** — existing call sites that omit them behave exactly as before.
  - Available in all three access modes:
    - **Library**: keyword arguments on every search function and on `QuranDatabase` methods
    - **CLI**: `--surah-hint SURAH` and `--start-after SURAH:AYAH` flags on `search`, `fuzzy`, `sliding-window`, and `smart-search` commands
    - **REST API**: `surah_hint`, `start_after_surah`, and `start_after_ayah` query parameters on `/search`, `/fuzzy-search`, `/sliding-window`, and `/smart-search` (pairing `start_after_surah` without `start_after_ayah` returns HTTP 400)

- **🔮 Semantic Vector Search**: New hybrid semantic search powered by sentence-transformers and FAISS
  - **Dual retrieval mode** controlled by `asymmetric` parameter (default `True`):
    - **Asymmetric** (`asymmetric=True`): `intfloat/multilingual-e5-base` (768-dim) + BM25Okapi lexical retrieval fused via Reciprocal Rank Fusion (RRF, k=60). Best overall accuracy — exact Arabic terms are never drowned out by semantic similarity
    - **Symmetric** (`asymmetric=False`): `paraphrase-multilingual-MiniLM-L12-v2` (384-dim), FAISS cosine only. Lightweight alternative for paraphrase-style queries
  - **`semantic_only` flag** (`False` by default): skips BM25+RRF in asymmetric mode and uses pure FAISS cosine ranking when `True`
  - **Partial ayah detection**: `start_word`/`end_word` fields indicate which portion of a verse matched (e.g. querying the first half of Ayat al-Kursi returns `2:255` with the precise word range)
  - **Surah-scoped expanding window**: `surah_hint` parameter initially restricts search to one surah, then expands ±1, ±2, … until a confident match is found
  - **Positional gravity**: `start_after=(surah, ayah)` boosts results that appear later in the Quran (15 % RRF score boost, ranking-only — does not inflate reported similarity)
  - **Sequence detection**: queries longer than 1.3× the best-matching verse automatically include the next 1–3 consecutive verses in the result
  - **Pre-built index script**: `scripts/build_vector_index.py` builds all five artefacts in one run:
    - `resources/vector/faiss_index.bin` — asymmetric dense index
    - `resources/vector/vindex_mapping.json` — asymmetric vector-ID → (surah, ayah) mapping
    - `resources/vector/bm25_index.pkl` — BM25Okapi lexical index
    - `resources/vector/faiss_sym_index.bin` — symmetric dense index
    - `resources/vector/vindex_sym_mapping.json` — symmetric mapping
  - **`make build-vector-index`** Makefile target for index construction
  - Available in all three access modes:
    - **Library**: `VectorSearch` class and `vector_search()` convenience function
    - **CLI**: `qal vector-search <query>` with `--asymmetric/--symmetric`, `--semantic-only`, `--surah-hint`, `--start-after`, `--threshold`, `--normalize` flags
    - **REST API**: `GET /vector-search` endpoint with equivalent query parameters
  - Optional extras: `pip install "quran-ayah-lookup[vector]"` (`sentence-transformers`, `faiss-cpu`, `rank-bm25`)
  
- **📚 Multi-Database Cache**: Multiple Quran text styles can now be loaded and used simultaneously without evicting one another
  - `get_quran_database()` with no arguments returns the default configured database (behaviour unchanged)
  - `get_quran_database(QuranStyle.X)` checks the in-memory cache for style X; loads it from disk on the first call, then serves subsequent calls from cache — the current default is never changed
  - `switch_quran_style(new_style)` updates the default style while keeping every previously loaded database in the cache; loaded databases are never discarded
  - `initialize_quran_database(style)` is now cache-aware per style: calling it twice for the same style returns the same object without reloading
  - All previous usage patterns remain fully backward compatible

### Fixed

- **🔧 Correct `corpus_style` for non-default styles**: `QuranLoader` now correctly sets `self.style` when an explicit style override is passed to the constructor. Previously, `load_quran_data()` always stamped the env-configured default style in `corpus_style` even when the data was loaded from a different style file, making `db.corpus_style` unreliable for non-default styles.

## [0.1.5] - 2026-01-24

### Added

- **📚 Multiple Quran Text Styles**: Added support for 6 different Quran text styles from Tanzil.net
  - `UTHMANI_ALL` (default): Full Uthmani script with all tashkeel and harakat (most complete)
  - `UTHMANI`: Uthmani script with standard diacritics
  - `SIMPLE`: Simplified text with basic diacritics
  - `SIMPLE_PLAIN`: Plain simplified text
  - `SIMPLE_CLEAN`: Cleaned simplified text
  - `SIMPLE_MINIMAL`: Minimal simplified text (least diacritics)
  - All corpus files available in `src/quran_ayah_lookup/resources/`

- **🔄 Style Switching Methods**: Three flexible ways to switch between Quran text styles
  - **Environment Variable**: `QAL_STYLE` environment variable support (works from shell or `.env` file)
  - **CLI Option**: `--style` / `-s` flag available for all CLI commands
  - **Python API**: Multiple methods for programmatic style control:
    - `get_quran_database(QuranStyle.SIMPLE)`: Initialize with specific style
    - `switch_quran_style(QuranStyle.SIMPLE)`: Dynamically switch styles
    - `initialize_quran_database(QuranStyle.SIMPLE)`: Manual initialization with style
    - `default_settings.style`: Direct settings modification

- **⚙️ Environment File Support**: `.env` file support for persistent style configuration
  - Set `QAL_STYLE=SIMPLE` in `.env` file for project-wide style defaults
  - Automatic loading of environment variables on package initialization

- **🎨 QuranStyle Enum**: New enumeration for type-safe style selection
  - All available styles exposed as `QuranStyle` enum members
  - Prevents invalid style names and provides IDE autocomplete support

### Changed

- **📖 Enhanced Documentation**: Comprehensive README updates for style management
  - Added "Quran Text Styles" section with detailed usage examples
  - Documented all three style switching methods with code examples
  - Included CLI usage examples for `--style` option
  - Added environment variable configuration examples

- **🏗️ Default Style**: Changed default to `UTHMANI_ALL` (previously `quran-uthmani_all.txt`)
  - Maintains all tashkeel and harakat for most complete Quranic text
  - Ensures backward compatibility with existing usage patterns

### Fixed

- **⚡ CLI Import Order**: Fixed import sequence in CLI module to respect `autoload_on_import` setting
  - Settings modification now occurs before package imports
  - Prevents premature database initialization with wrong style
  - Ensures CLI style options are properly applied

### Credits
- Thanks to [@legeRise](https://github.com/legeRise) for suggesting multiple text styles and environment variable support!

## [0.1.4] - 2025-10-27

### Changed

- **🔍 Boundary Refinement for Long Queries**: Smart boundary detection for queries > 100 characters instead of 500 characters

## [0.1.3] - 2025-10-24

### Added

- **📦 JSON Serialization Support**: Added `to_dict()` methods to all data models
  - `QuranVerse.to_dict()`: Convert verse to dictionary
  - `FuzzySearchResult.to_dict()`: Convert search result with nested verse data
  - `MultiAyahMatch.to_dict()`: Convert multi-ayah match with verses list
  - `QuranChapter.to_dict(include_verses)`: Convert chapter with optional verse data
  - `QuranDatabase.to_dict(include_verses, include_surahs)`: Convert database with flexible output control
  - All nested objects are recursively converted for proper JSON serialization
  - Enables easy API responses and data export functionality

- **🎯 Partial Verse Range Retrieval**: New `get_partial_verses()` method in `QuranDatabase`
  - Get a range of verses from start ayah to end ayah (inclusive)
  - Input: Two tuples `(surah_number, ayah_number)` for start and end
  - Handles single-surah and multi-surah ranges
  - Comprehensive validation of surah numbers, ayah numbers, and range validity
  - Returns ordered list of `QuranVerse` objects
  - Example: `db.get_partial_verses((1, 1), (1, 7))` gets Al-Fatihah verses 1-7

- **🔍 Boundary Refinement for Long Queries**: Smart boundary detection for queries > 500 characters
  - New `refine_sliding_window_result()` function for precise boundary refinement
  - Uses first and last 30 characters of query for recursive boundary detection
  - Searches within ±5 ayah context window around initial boundaries
  - Only applies refinement if new boundaries are within initial boundaries
  - Prevents over-matching in long text searches
  - Improves accuracy for multi-ayah queries

- **⚡ Enhanced Cache Optimization**: Improved sliding window search cache usage
  - Made `verses` parameter optional in `sliding_window_multi_ayah_search()`
  - Added `search_entire_db` flag to track when searching full Quran
  - Cache only used when searching entire database (prevents overriding user-provided verse lists)
  - Automatic database loading when no verses provided
  - Updated `search_sliding_window()` wrapper to leverage cache by default

### Changed

- **♻️ Code Refactoring**: Improved readability and maintainability
  - Extracted boundary refinement logic into separate `refine_sliding_window_result()` function
  - Reduced `sliding_window_multi_ayah_search()` complexity by ~100 lines
  - Better separation of concerns for easier testing and maintenance

- **📚 Enhanced Documentation**: Updated docstrings with new examples
  - Added examples for automatic database loading
  - Documented cache behavior with `search_entire_db` flag
  - Clarified usage patterns for partial verse retrieval

### Fixed

- **🔧 Type Checking**: Added `MultiAyahMatch` to TYPE_CHECKING imports in `text_utils.py`
  - Resolves Pylance type checking warnings
  - Proper type hints for `refine_sliding_window_result()` function

## [0.1.2] - 2025-10-22

### Fixed

- **📦 Package Distribution**: Fixed missing Quran text resource file in built packages
  - Added `recursive-include src/quran_ayah_lookup/resources *.txt` to `MANIFEST.in`
  - Added `[tool.setuptools.package-data]` section to `pyproject.toml`
  - Ensures `quran-uthmani_all.txt` is included in both source and wheel distributions
  - Package now installs correctly with all required resource files

## [0.1.1] - 2025-10-17

### Added

- **⚡ 207x Faster Sliding Window**: Complete algorithm rewrite using alignment-based approach

  - New implementation using `rapidfuzz.fuzz.partial_ratio_alignment()` for iterative match finding
  - Character-to-word mapping with `bisect.bisect_right()` for O(log n) lookups
  - Iterative slicing from end of each match to find all occurrences
  - **Performance**: ~54ms per query (was ~11,150ms) = 207x improvement!
  - Maintains high accuracy: 97.1-100.0% similarity scores
  - Comprehensive algorithm documentation in `docs/implementation/ALIGNMENT_ALGORITHM_UPDATE.md`

- **💾 Performance Cache System**: Pre-computed corpus and word lists for optimal speed

  - New `__enable_cache__` flag in package initialization (default: `True`)
  - Pre-computed full corpus text (720,944 chars original, 405,394 normalized)
  - Pre-split word lists (82,459 original words, 77,881 normalized)
  - Pre-sorted reference lists (114 surahs, 6,348 ayah tuples)
  - Character-to-word offset mappings for O(log n) position lookups
  - **Performance**: ~28% speedup with cache enabled (54ms vs 69ms)
  - `finalize_cache()` method in `QuranDatabase` to build cache structures
  - Detailed cache documentation in `docs/implementation/PERFORMANCE_ENHANCEMENTS.md`

- **📊 Basmalah-Aware Counting**: Precise verse counts with or without Basmalas

  - New `get_verse_count(include_basmalah: bool = False)` method in `QuranDatabase`
  - `total_verses_without_basmalah` attribute (6,236 verses)
  - Accurate distinction between total Quranic verses (6,236) and database entries (6,348)
  - Updated `get_all_verses()` to include Basmalas by default
  - Fixed test suite to account for Basmala counting

- **🎯 Absolute Indexing**: O(1) access to any verse by absolute position

  - Pre-sorted ayah reference list (6,348 tuples)
  - Enables sequential verse iteration
  - Foundation for future pagination and export features
  - Efficient batch operations across entire Quran

- **📚 Comprehensive Documentation**: Three new implementation documents
  - `docs/implementation/ALIGNMENT_ALGORITHM_UPDATE.md`: Complete algorithm rewrite details
  - `docs/implementation/PERFORMANCE_ENHANCEMENTS.md`: Cache system and basmalah features
  - `docs/implementation/SLIDING_WINDOW_CACHE_ANALYSIS.md`: Performance benchmarks and analysis
  - Updated README.md with new performance features and examples
  - Updated docs/index.md and docs/quickstart.md with performance sections

### Changed

- **Sliding Window Algorithm**: Complete rewrite from vectorized to alignment-based approach

  - Replaced `rapidfuzz.process.cdist()` with `fuzz.partial_ratio_alignment()`
  - Improved algorithm complexity from O(n\*m) to near-linear iterative approach
  - Better memory efficiency with incremental processing
  - More predictable performance characteristics

- **API Signature**: Updated `search_sliding_window()` to accept `db` parameter

  - Enables cache reuse across multiple searches
  - Maintains backward compatibility (db auto-loaded if not provided)
  - Better performance for batch search operations

- **Database Loading**: Enhanced initialization sequence
  - Cache finalization now occurs during `load_quran_db()` when cache is enabled
  - One-time cache build cost during database initialization
  - Subsequent searches benefit from pre-computed structures

### Performance

- **Sliding Window Search**: 207x faster (54ms vs 11,150ms per query)
- **Cache Impact**: 28% speedup when cache is enabled (54ms vs 69ms)
- **Accuracy**: Maintained high precision (97.1-100.0% similarity scores)
- **Memory**: Modest cache overhead (~2MB for corpus and word lists)

### Fixed

- **Test Suite**: Fixed `test_get_surah_chapter` to account for Basmala in verse counts
  - Updated expected count calculation: `len(surah) + (1 if surah.has_basmala() else 0)`
  - All 152 tests now passing

## [0.1.0] - 2025-10-17

### Added

- **🔄 Sliding Window Search**: Multi-ayah text matching with vectorized fuzzy matching

  - `search_sliding_window()` function for finding text spanning multiple consecutive ayahs
  - Vectorized fuzzy matching using `rapidfuzz.process.cdist` for high performance
  - Dynamic window sizing and stride optimization for long queries
  - Cross-surah matching capability
  - Configurable similarity thresholds (0.0-100.0)
  - CLI command: `qal sliding-window <query> [--threshold 80.0] [--limit N]`
  - REST API endpoint: `GET /sliding-window`
  - Returns `MultiAyahMatch` objects with verse ranges and similarity scores

- **🧠 Smart Search**: Intelligent automatic method selection

  - `smart_search()` function with cascading search strategy
  - Automatic method selection: exact text search → fuzzy search → sliding window search
  - Transparent method reporting and type-safe result handling
  - CLI command: `qal smart-search <query> [--fuzzy-threshold 0.7] [--sliding-threshold 80.0]`
  - REST API endpoint: `GET /smart-search`
  - Returns structured results with method used, results, and count

- **📊 MultiAyahMatch Data Model**: New dataclass for multi-ayah search results

  - Word-level position tracking across verse boundaries
  - `get_reference()` method for formatted verse references (e.g., "55:1-4")
  - Support for cross-surah matches
  - Similarity scoring and verse range information

- **🌐 REST API Server**: Complete HTTP API with FastAPI framework

  - 8 comprehensive endpoints exposing all package functionalities
  - Automatic Swagger/OpenAPI documentation at `/docs`
  - Interactive API documentation at `/redoc`
  - CLI command: `qal serve` to start API server
  - Optional API dependencies: `fastapi>=0.104.0`, `uvicorn[standard]>=0.24.0`

- **🔧 Dependencies**: Added numpy for vectorized operations

  - `numpy>=2.0.0` as core dependency (required by rapidfuzz.cdist)
  - Maintains compatibility with existing rapidfuzz and click dependencies

- **📚 Documentation**: Comprehensive updates for new features

  - Complete API documentation in `docs/api.md` including REST endpoints
  - Practical examples in `docs/quickstart.md`
  - Updated `README.md` with new features and usage examples
  - Implementation documentation organized in `docs/implementation/`
  - REST API endpoint documentation with request/response examples

- **🧪 Testing**: Extensive test coverage for new functionality
  - 18 comprehensive tests for sliding window functionality
  - 22 comprehensive tests for smart search functionality
  - 36 comprehensive API tests for REST endpoints
  - All 152 tests passing (112 existing + 40 new)

### Changed

- **Version Management**: Updated to use dynamic versioning from `importlib.metadata`
- **Package Structure**: Organized implementation documentation in dedicated directory
- **Dependencies**: Added numpy to core dependencies for vectorized operations

### Fixed

- **Version Resolution**: Fixed dynamic version loading from package metadata

## [0.0.2] - 2025-10-14

### Added

- **CLI Interface**: Complete command-line interface with Click framework
  - `qal` and `quran-ayah-lookup` command entry points
  - Interactive REPL mode with Ctrl+C exit support
  - All package functions mapped to CLI commands:
    - `verse <surah> <ayah>` - Get specific verses with optional text normalization
    - `surah <number>` - Display surah information and verse counts
    - `search <query>` - Exact substring search across all verses
    - `fuzzy <query>` - Fuzzy search with similarity scoring and thresholds
    - `list-verses <surah>` - List all verses in a specific surah
    - `stats` - Display database statistics
- **Comprehensive CLI Documentation**: Updated README with CLI usage examples and REPL mode guide
- **Unit Tests**: 42 comprehensive test cases covering all CLI functionality
- **Dependencies**: Added Click framework for CLI implementation
- **Error Handling**: Meaningful error messages and graceful exit handling

### Changed

- **Package Dependencies**: Added Click >= 8.0.0 to core dependencies
- **README**: Enhanced with CLI usage section and interactive examples
- **Build Configuration**: Added console script entry points in pyproject.toml

### Notes

- CLI provides full access to all package functionality through command line
- Interactive REPL mode allows continuous queries without restarting
- All existing functionality remains unchanged and backward compatible
- Package now supports both programmatic and command-line usage patterns

## [0.0.1] - 2025-10-09

### Added

- Initial package structure
- MIT License
- README with project description
- pyproject.toml configuration
- Development dependencies setup
- Documentation directory structure
- Contributing guidelines
- .gitignore for Python development

### Notes

- This is the initial release with package structure only
- Core functionality implementation is pending
- Package is ready for PyPI publication structure-wise
