#!/usr/bin/env python3
"""
Quick test script to verify Ctrl+C handling in REPL mode.
Run this and press Ctrl+C to test the exit behavior.
"""
from quran_ayah_lookup.cli import cli

if __name__ == "__main__":
    print("Starting REPL - Press Ctrl+C to test exit behavior")
    print("-" * 60)
    cli()
