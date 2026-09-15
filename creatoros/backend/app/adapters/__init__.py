"""Adapters — hexagonal ports & adapters implementation.

- `primary`: driven by the outside world (FastAPI HTTP API)
- `secondary`: drive external systems (instagrapi, session persistence)
"""
from __future__ import annotations
