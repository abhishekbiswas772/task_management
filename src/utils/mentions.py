"""
Helpers for mention parsing.
"""
from __future__ import annotations

import re

MENTION_RE = re.compile(r"(?<![\w@])@([A-Za-z0-9_.-]{3,80})")


def extract_mentions(*parts: str | None) -> list[str]:
    mentions: list[str] = []
    seen: set[str] = set()
    for part in parts:
        if not part:
            continue
        for match in MENTION_RE.findall(part):
            key = match.lower()
            if key in seen:
                continue
            seen.add(key)
            mentions.append(match)
    return mentions
