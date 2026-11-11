"""Shared text tokenisation for BM25 and the offline hashing embedder."""

import re
from typing import List

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> List[str]:
    """Lowercase alphanumeric tokens."""
    return _TOKEN_RE.findall(text.lower())
