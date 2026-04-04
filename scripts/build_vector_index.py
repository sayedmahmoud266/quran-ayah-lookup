#!/usr/bin/env python3
"""
Build vector indexes for semantic search (both asymmetric and symmetric modes).

**Asymmetric index** (intfloat/multilingual-e5-base + BM25):
  - Uses ``"passage: "`` prefix for corpus encoding at index time.
  - Queries must use ``"query: "`` prefix at search time (handled by VectorSearch).
  - Output: ``faiss_index.bin``, ``vindex_mapping.json``, ``bm25_index.pkl``

**Symmetric index** (paraphrase-multilingual-MiniLM-L12-v2):
  - No prefix required; queries and passages are encoded identically.
  - Output: ``faiss_sym_index.bin``, ``vindex_sym_mapping.json``

Usage:
    python scripts/build_vector_index.py [--style STYLE]

Requires:
    pip install "quran-ayah-lookup[vector]"

Output files (all in src/quran_ayah_lookup/resources/vector/):
    faiss_index.bin
    vindex_mapping.json
    bm25_index.pkl
    faiss_sym_index.bin
    vindex_sym_mapping.json
"""

import argparse
import json
import os
import pickle
import sys

# Allow running from the repo root without the package being installed
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO_ROOT, "src"))

_OUT_DIR = os.path.join(
    _REPO_ROOT, "src", "quran_ayah_lookup", "resources", "vector"
)

# Asymmetric (e5-base + BM25)
_INDEX_PATH = os.path.join(_OUT_DIR, "faiss_index.bin")
_MAPPING_PATH = os.path.join(_OUT_DIR, "vindex_mapping.json")
_BM25_PATH = os.path.join(_OUT_DIR, "bm25_index.pkl")
_MODEL_NAME = "intfloat/multilingual-e5-base"

# Symmetric (MiniLM)
_SYM_INDEX_PATH = os.path.join(_OUT_DIR, "faiss_sym_index.bin")
_SYM_MAPPING_PATH = os.path.join(_OUT_DIR, "vindex_sym_mapping.json")
_SYM_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build FAISS vector indexes for quran-ayah-lookup semantic search."
    )
    parser.add_argument(
        "--style",
        default="UTHMANI_ALL",
        help="Quran text style to index (default: UTHMANI_ALL).",
    )
    args = parser.parse_args()

    # --- verify optional deps ---
    try:
        import faiss
        import numpy as np
        from rank_bm25 import BM25Okapi
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        print(
            "Error: Vector extras not installed.\n"
            'Run: pip install "quran-ayah-lookup[vector]"',
            file=sys.stderr,
        )
        print(f"Details: {exc}", file=sys.stderr)
        sys.exit(1)

    # --- import the package ---
    try:
        from quran_ayah_lookup import QuranStyle, get_quran_database
    except ImportError as exc:
        print(
            "Error: quran-ayah-lookup is not importable.\n"
            "Run: pip install -e .",
            file=sys.stderr,
        )
        print(f"Details: {exc}", file=sys.stderr)
        sys.exit(1)

    # --- resolve style ---
    try:
        style = QuranStyle[args.style.upper()]
    except KeyError:
        valid = [s.name for s in QuranStyle]
        print(
            f"Error: Unknown style '{args.style}'. Valid styles: {valid}",
            file=sys.stderr,
        )
        sys.exit(1)

    # --- load database ---
    print(f"Loading Quran database (style: {style.name}) ...")
    db = get_quran_database(style)
    all_verses = db.get_all_verses()
    print(f"  {len(all_verses)} verses loaded.")

    # --- build mapping (same verse order for both models) ---
    mapping = [
        {"surah": verse.surah_number, "ayah": verse.ayah_number}
        for verse in all_verses
    ]

    os.makedirs(_OUT_DIR, exist_ok=True)

    # ======================================================================
    # Part 1: Asymmetric index (intfloat/multilingual-e5-base + BM25)
    # ======================================================================
    print(f"\n[Asymmetric] Loading model: {_MODEL_NAME} ...")
    model_asym = SentenceTransformer(_MODEL_NAME)

    print("[Asymmetric] Encoding verses with 'passage: ' prefix ...")
    texts_asym = ["passage: " + verse.text_normalized for verse in all_verses]
    embeddings_asym = model_asym.encode(
        texts_asym,
        batch_size=128,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype("float32")

    dim_asym = embeddings_asym.shape[1]
    print(f"[Asymmetric] Building FAISS IndexFlatIP (dim={dim_asym}) ...")
    index_asym = faiss.IndexFlatIP(dim_asym)
    index_asym.add(embeddings_asym)
    print(f"[Asymmetric] Index contains {index_asym.ntotal} vectors.")

    print("[Asymmetric] Building BM25Okapi index ...")
    tokenized_corpus = [verse.text_normalized.split() for verse in all_verses]
    bm25 = BM25Okapi(tokenized_corpus)
    print(f"[Asymmetric] BM25 index built over {len(tokenized_corpus)} documents.")

    print(f"[Asymmetric] Saving FAISS index  -> {_INDEX_PATH}")
    faiss.write_index(index_asym, _INDEX_PATH)

    print(f"[Asymmetric] Saving ID mapping   -> {_MAPPING_PATH}")
    with open(_MAPPING_PATH, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False)

    print(f"[Asymmetric] Saving BM25 index   -> {_BM25_PATH}")
    with open(_BM25_PATH, "wb") as f:
        pickle.dump(bm25, f)

    # ======================================================================
    # Part 2: Symmetric index (paraphrase-multilingual-MiniLM-L12-v2)
    # ======================================================================
    print(f"\n[Symmetric] Loading model: {_SYM_MODEL_NAME} ...")
    model_sym = SentenceTransformer(_SYM_MODEL_NAME)

    print("[Symmetric] Encoding verses (no prefix) ...")
    texts_sym = [verse.text_normalized for verse in all_verses]
    embeddings_sym = model_sym.encode(
        texts_sym,
        batch_size=128,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype("float32")

    dim_sym = embeddings_sym.shape[1]
    print(f"[Symmetric] Building FAISS IndexFlatIP (dim={dim_sym}) ...")
    index_sym = faiss.IndexFlatIP(dim_sym)
    index_sym.add(embeddings_sym)
    print(f"[Symmetric] Index contains {index_sym.ntotal} vectors.")

    print(f"[Symmetric] Saving FAISS index  -> {_SYM_INDEX_PATH}")
    faiss.write_index(index_sym, _SYM_INDEX_PATH)

    print(f"[Symmetric] Saving ID mapping   -> {_SYM_MAPPING_PATH}")
    with open(_SYM_MAPPING_PATH, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False)

    # ======================================================================
    # Summary
    # ======================================================================
    print("\nDone! Both indexes built successfully.")
    print(f"\nAsymmetric (e5-base + BM25):")
    print(f"  FAISS   : {_INDEX_PATH}")
    print(f"  Mapping : {_MAPPING_PATH}")
    print(f"  BM25    : {_BM25_PATH}")
    print(f"\nSymmetric (MiniLM):")
    print(f"  FAISS   : {_SYM_INDEX_PATH}")
    print(f"  Mapping : {_SYM_MAPPING_PATH}")


if __name__ == "__main__":
    main()
