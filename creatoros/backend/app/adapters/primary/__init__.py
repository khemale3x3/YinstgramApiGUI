"""Primary (driving) adapters.

These are the entry points driven BY the outside world — in practice the
FastAPI HTTP API. They translate HTTP into use-case calls and depend only on
the application services and schemas.
"""
from __future__ import annotations
