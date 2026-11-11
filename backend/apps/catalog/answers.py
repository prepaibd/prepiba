"""Answer resolution for imported questions.

The source data stores answers inconsistently: a letter, the option text, a letter
with a gloss ("A (50%)"), a GMAT-style sentence, a multi-answer ("A and B"),
free text, or nothing. `resolve_answer` turns that into a canonical outcome and an
honest verification status. No printed answer keys exist in the source PDFs, so
nothing is ever 'verified' from the PDF; 'verified' means the legacy key and the
independently derived solution agree.
"""
import re
from dataclasses import dataclass

LABELS = "ABCDE"

# Standard data-sufficiency choices; used only when the instruction cannot be parsed.
DS_FALLBACK = {
    "A": "Statement 1 alone is sufficient, but statement 2 alone is not sufficient to answer the question.",
    "B": "Statement 2 alone is sufficient, but statement 1 alone is not sufficient to answer the question.",
    "C": "Both statements taken together are sufficient to answer the question, "
         "but neither statement alone is sufficient.",
    "D": "Each statement alone is sufficient.",
    "E": "Statements 1+2 together aren't sufficient, and additional data is needed to answer the question.",
}

_GMAT = re.compile(r"GMAT-style:\s*([A-E])\b")
_LEAD = re.compile(r"^([A-E])\s*\(")
_BLANK_KEYS = (None, "")


def parse_ds_options(instruction: str) -> dict[str, str]:
    found = {}
    for line in (instruction or "").splitlines():
        m = re.match(r"^\s*([A-E])\.\s*(.+?)\s*$", line)
        if m:
            found[m.group(1)] = m.group(2)
    return found if len(found) == 5 else dict(DS_FALLBACK)


def to_label(raw, options: dict[str, str]):
    """Map a raw stored answer to an option label, or None if it cannot be mapped."""
    if raw in _BLANK_KEYS:
        return None
    s = str(raw).strip()
    if s.upper() in options and len(s) == 1:
        return s.upper()
    m = _GMAT.search(s) or _LEAD.match(s)
    if m and m.group(1) in options:
        return m.group(1)
    low = s.lower()
    hits = [lab for lab, text in options.items() if text.strip().lower() == low]
    return hits[0] if len(hits) == 1 else None


@dataclass
class Resolved:
    kind: str  # mcq | text | essay
    correct_label: str | None
    answer_text: str
    status: str  # verified | derived | unverified | disputed | none
    source: str
    prev: str


def resolve_answer(qtype: str, legacy, solution, options: dict[str, str]) -> Resolved:
    legacy = None if legacy in _BLANK_KEYS else str(legacy).strip()
    solution = None if solution in _BLANK_KEYS else str(solution).strip()

    if qtype == "essay":
        return Resolved("essay", None, "", "none", "", "")

    if not options:  # free-response: numeric / short text, never auto-scored
        if legacy is None and solution is None:
            if qtype == "argument":
                return Resolved("essay", None, "", "none", "", "")
            return Resolved("text", None, "", "unverified", "", "")
        chosen = solution or legacy
        if solution and legacy and _norm(solution) == _norm(legacy):
            return Resolved("text", None, chosen, "verified", "legacy+solution_agree", "")
        if solution and legacy:
            return Resolved("text", None, chosen, "disputed", "solution_overrode_legacy", legacy)
        if solution:
            return Resolved("text", None, chosen, "derived", "solution", "")
        return Resolved("text", None, chosen, "unverified", "legacy", "")

    leg = to_label(legacy, options)
    sol = to_label(solution, options)
    prev = legacy if (legacy and legacy != leg) else ""
    if leg and sol:
        if leg == sol:
            return Resolved("mcq", sol, "", "verified", "legacy+solution_agree", prev)
        return Resolved("mcq", sol, "", "disputed", "solution_overrode_legacy", leg)
    if sol:
        return Resolved("mcq", sol, "", "derived", "solution", prev)
    if leg:
        return Resolved("mcq", leg, "", "unverified", "legacy", prev)
    raw = solution or legacy
    if raw:  # present but not mappable, e.g. "A and B"
        return Resolved("mcq", None, raw, "disputed", "unmappable_answer", "")
    return Resolved("mcq", None, "", "unverified", "", "")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())
