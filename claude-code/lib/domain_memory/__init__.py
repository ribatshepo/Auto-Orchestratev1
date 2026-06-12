"""Domain memory — project-level, cross-session knowledge store.

Provides persistent, queryable domain knowledge that grows across all
pipeline sessions (auto-orchestrate, auto-debug, auto-audit). All stores
use append-only JSONL with file-level locking for concurrency safety.

Location: ``.orchestrate/domain/`` at the project root (legacy ``.domain/``
remains readable via :mod:`claude_code.lib.path_compat`).

Dependencies: Python >= 3.11 stdlib only.
"""

from __future__ import annotations

from .schemas import (
    CodebaseAnalysisEntry,
    DecisionEntry,
    FixEntry,
    PatternEntry,
    ResearchEntry,
    UserPreferenceEntry,
)
from .indexer import DomainIndexer
from .store import DomainMemoryStore

__all__ = [
    "DomainMemoryStore",
    "DomainIndexer",
    "ResearchEntry",
    "DecisionEntry",
    "PatternEntry",
    "FixEntry",
    "CodebaseAnalysisEntry",
    "UserPreferenceEntry",
]
