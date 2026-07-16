#!/usr/bin/env python3
"""Lint the pinned device-alias vocabulary and its complete product-copy review."""

import pathlib
import re
import sys

sys.dont_write_bytecode = True


def repo_root():
    here = pathlib.Path(__file__).resolve().parent
    for candidate in (here, *here.parents):
        if (candidate / "dashboard" / "device_aliases.py").is_file():
            return candidate
    raise RuntimeError("cannot locate repository")


ROOT = repo_root()
sys.path.insert(0, str(ROOT / "dashboard"))
import device_aliases

REVIEW = pathlib.Path(__file__).with_name("word-list-review.md").read_text(encoding="utf-8")
TOKEN_RE = re.compile(r"^[A-Za-z]{2,12}$")
GIVEN_REVIEW = REVIEW.split("## Given names (64)", 1)[1].split("## Character words (64)", 1)[0]
WORD_REVIEW = REVIEW.split("## Character words (64)", 1)[1].split("## Manual review checklist", 1)[0]


def check(label, condition, detail=""):
    if not condition:
        raise AssertionError(f"{label}: {detail}")
    print(f"PASS {label}")


given = device_aliases.GIVEN_NAMES
words = device_aliases.CHARACTER_WORDS
check("Freda Sparks anchors generator v1", given[0] == "Freda" and words[0] == "Sparks")
check("both pinned vocabularies contain 64 entries", len(given) == len(words) == 64)
check("given names are case-insensitively unique", len({item.casefold() for item in given}) == 64)
check("character words are case-insensitively unique", len({item.casefold() for item in words}) == 64)
check("all tokens are short ASCII alphabetic words",
      all(TOKEN_RE.fullmatch(item) and item.isascii() for item in (*given, *words)))
check("all 4096 generated pairs satisfy the public alias grammar",
      all(device_aliases.clean_alias(f"{name} {word}") == f"{name} {word}"
          for name in given for word in words))
check("review artifact contains every given name exactly once",
      all(GIVEN_REVIEW.count(f"`{item}`") == 1 for item in given))
check("review artifact contains every character word exactly once",
      all(WORD_REVIEW.count(f"`{item}`") == 1 for item in words))
check("review artifact records the human language boundary",
      "Bob's ratified human direction" in REVIEW
      and "not a claim that Bob approved every token individually" in REVIEW)

print("\n9/9 word-list checks passed")
