"""Ports — the interfaces at the hexagonal boundary.

Ports define *what* the application needs, never *how* it is done. The domain
and use-cases depend only on these abstractions. Concrete adapters live in
`app.adapters.secondary` and implement these ports.
"""
from __future__ import annotations
