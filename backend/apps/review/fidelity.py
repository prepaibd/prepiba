"""Bangla must not change what the English question says.

Ported from tools/check_bn.py: numbers and $..$ LaTeX must match the English exactly and Bangla digits
are not allowed (the exam uses 0-9). See docs/BANGLA_STYLE_GUIDE.md.
"""
import re
from collections import Counter

_NUM = re.compile(r"\d+(?:\.\d+)?")
_LATEX = re.compile(r"\$[^$]*\$")
_BN_DIGITS = re.compile("[০-৯]")
_PREFIX = re.compile(r"^\s*\d+\s*[.)]\s+")


def _latex(s: str) -> Counter:
    return Counter(_LATEX.findall(s.replace("\\$", "DOLLAR")))


def problems(english: str, bangla: str, what: str = "text") -> list[str]:
    """Reasons `bangla` is not a faithful rendering of `english` (empty list = fine)."""
    out = []
    english = _PREFIX.sub("", english or "")
    if _NUM.findall(english) and Counter(_NUM.findall(english)) != Counter(_NUM.findall(bangla)):
        out.append(f"{what}: numbers differ from the English "
                   f"(English {dict(Counter(_NUM.findall(english)))}, Bangla {dict(Counter(_NUM.findall(bangla)))})")
    elif not _NUM.findall(english) and _NUM.findall(bangla):
        out.append(f"{what}: Bangla contains numbers the English does not")
    if _latex(english) != _latex(bangla):
        out.append(f"{what}: LaTeX ($...$) differs from the English")
    if _BN_DIGITS.search(bangla):
        out.append(f"{what}: use digits 0-9, not Bangla digits")
    return out
