from __future__ import annotations
"""Utilities for normalizing and comparing hardware barcodes."""

import re
"""Barcode normalisation helpers explained for newcomers.

Many data sources use slightly different formats for the same barcode. These
functions reveal *what* transformations happen, *when* we apply them (during
inventory lookups), *why* they matter (to avoid duplicates), and *how* the code
arrives at consistent results.
"""

from __future__ import annotations

import re
from typing import List

__all__ = ["normalize_barcode", "barcode_aliases"]


_NON_ALPHA_RE = re.compile(r"[A-Za-z]")
_DIGIT_ONLY_RE = re.compile(r"\D")


def _strip_and_collapse(value: str) -> str:
    """Trim surrounding whitespace and squash repeated spaces into one."""

    value = value.strip()
    # Collapse internal whitespace to single spaces to avoid mismatched spacing
    value = re.sub(r"\s+", " ", value)
    return value


def normalize_barcode(raw: str | None) -> str | None:
    """Return a canonical representation for a barcode value.

    * Trims outer whitespace and collapses repeated internal whitespace.
    * When the value is numeric (allowing for punctuation/spacing), remove non-digit
      characters and coerce 12-digit codes into 13 digits by prefixing a leading zero.
    * Upper-case any alpha characters for consistency.
    """

    if raw is None:
        return None

    cleaned = _strip_and_collapse(raw)
    if not cleaned:
        return None

    if not _NON_ALPHA_RE.search(cleaned):
        digits = _DIGIT_ONLY_RE.sub("", cleaned)
        if digits:
            if len(digits) == 12:
                digits = "0" + digits
            return digits

    return cleaned.upper()


def barcode_aliases(raw: str | None) -> list[str]:
    """Return potential barcode variants that should be considered equivalent."""

    if raw is None:
        return []

    cleaned = _strip_and_collapse(raw)
    if not cleaned:
        return []

    aliases: List[str] = []
    seen: set[str] = set()

    def add(candidate: str | None) -> None:
        """Safely append a candidate alias to the list if it is new and non-empty."""

        if not candidate:
            return
        if candidate in seen:
            return
        seen.add(candidate)
        aliases.append(candidate)

    canonical = normalize_barcode(cleaned)
    add(canonical)

    if not _NON_ALPHA_RE.search(cleaned):
        digits = _DIGIT_ONLY_RE.sub("", cleaned)
        if digits:
            add(digits)
            if len(digits) == 12:
                add("0" + digits)
            if len(digits) == 13 and digits.startswith("0"):
                add(digits[1:])

    add(cleaned.upper())

    return aliases
