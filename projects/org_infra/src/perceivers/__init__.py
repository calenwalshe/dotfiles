"""Perceivers — standalone scripts that ingest data and write L0 Claims.

Each perceiver is a plugin. It reads one data source, writes Claims to the store.
To add a new data source: write a new perceiver. No other component changes.
"""
