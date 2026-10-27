from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

LEGAL_SUFFIXES = re.compile(
    r"\b(llc|l\.l\.c|inc|incorporated|corp|corporation|company|co|pllc|pa)\b",
    flags=re.IGNORECASE,
)
NON_ALPHANUMERIC = re.compile(r"[^a-z0-9]+")
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def normalize_company_name(value: str | None) -> str:
    """Return a comparison-friendly company name."""

    if not value:
        return ""
    normalized = LEGAL_SUFFIXES.sub(" ", value.lower().replace("&", " and "))
    return " ".join(NON_ALPHANUMERIC.sub(" ", normalized).split())


def normalize_domain(value: str | None) -> str:
    if not value:
        return ""
    domain = value.strip().lower()
    domain = re.sub(r"^https?://", "", domain)
    domain = re.sub(r"^www\.", "", domain)
    return domain.split("/")[0]


def is_valid_email(value: str | None) -> bool:
    return bool(value and EMAIL_PATTERN.fullmatch(value.strip()))


def record_hash(record: Mapping[str, Any]) -> str:
    """Create a stable hash that is independent of dictionary key order."""

    payload = json.dumps(record, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
