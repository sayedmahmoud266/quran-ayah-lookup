# Documentation

Welcome to the Quran Ayah Lookup documentation - a high-performance Python package with **O(1) verse access** and **207x faster multi-ayah search**.

## Table of Contents

- [Installation Guide](installation.md)
- [Quick Start Guide](quickstart.md)
- [API Reference](api.md)
- [Contributing Guidelines](../CONTRIBUTING.md)

## Overview

This package provides lightning-fast tools for searching and looking up Quranic ayahs with O(1) performance and advanced Arabic text processing.

## Features

- 🚀 **O(1) Performance**: 956x faster than linear search with `db[surah][ayah]` syntax
- ⚡ **207x Faster Sliding Window**: New alignment-based algorithm (54ms vs 11s per query!)
- 💾 **Performance Cache**: Pre-computed corpus and word lists for optimal speed
- 📊 **Basmalah-Aware Counting**: Precise verse counts with/without Basmalas
- 🎯 **Absolute Indexing**: O(1) access to any verse by absolute position (0-6347)
- 📖 **Complete Quran Database**: 6,348 verses including smart Basmala handling
- 🔍 **Arabic Text Search**: Full-text search across all verses
- 🎯 **Fuzzy Search**: Partial text matching with configurable similarity thresholds
- 🔄 **Multi-Ayah Search**: Sliding window search for text spanning multiple verses
- 🧠 **Smart Search**: Automatic method selection for optimal results
- 🔤 **Advanced Text Normalization**: Diacritics removal and Alif normalization
- 🏗️ **Chapter-based Organization**: Efficient QuranChapter structure for O(1) access
- 💻 **CLI Interface**: Command-line tool with interactive REPL mode
- 🌐 **REST API**: HTTP endpoints with automatic Swagger documentation
- 🕌 **Arabic Only**: Focused on Arabic Quranic text (no translations)
- 📚 **Tanzil.net Corpus**: Trusted Quran text source

## Getting Help

If you need help or have questions:

1. Check the documentation files in this directory
2. Visit the [GitHub repository](https://github.com/sayedmahmoud266/quran-ayah-lookup)
3. Create an issue for bugs or feature requests
