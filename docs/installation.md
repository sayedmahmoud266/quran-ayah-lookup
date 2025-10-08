# Installation Guide

## Requirements

- Python 3.8 or higher
- pip package manager

## Installation Methods

### From PyPI (Recommended)

```bash
pip install quran-ayah-lookup
```

### From Source

1. Clone the repository:
```bash
git clone https://github.com/sayedmahmoud266/quran-ayah-lookup.git
cd quran-ayah-lookup
```

2. Install the package:
```bash
pip install -e .
```

### Development Installation

For development, install with development dependencies:

```bash
git clone https://github.com/sayedmahmoud266/quran-ayah-lookup.git
cd quran-ayah-lookup
pip install -e ".[dev]"
```

Or using requirements files:
```bash
pip install -r requirements-dev.txt
```

## Verification

Verify the installation:

```python
import quran_ayah_lookup
print(quran_ayah_lookup.__version__)
```

## Troubleshooting

### Common Issues

1. **Permission Errors**: Use `pip install --user` if you encounter permission issues
2. **Python Version**: Ensure you're using Python 3.8 or higher
3. **Virtual Environment**: Consider using a virtual environment for isolation

### Virtual Environment Setup

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install quran-ayah-lookup
```