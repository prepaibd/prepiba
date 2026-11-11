"""Turn raw model output into feedback we are willing to store and show. Model output is untrusted."""
import json
import re

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)
SCORES = ("overall", "content", "structure", "language")


def extract_json(raw: str) -> dict:
    """Parse the first JSON object in `raw` (tolerates code fences and chatter around it)."""
    text = _FENCE.sub("", (raw or "").strip())
    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON object in model output")
    obj, _ = json.JSONDecoder().raw_decode(text[start:])
    if not isinstance(obj, dict):
        raise ValueError("model output is not a JSON object")
    return obj


def _score(v) -> int:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ValueError("score is not a number")
    return max(0, min(10, round(v)))


def _strings(v, limit: int, max_len: int = 400) -> list[str]:
    if not isinstance(v, list):
        return []
    return [s.strip()[:max_len] for s in v if isinstance(s, str) and s.strip()][:limit]


def normalise(raw: str, essay: str) -> dict:
    """Validated feedback: scores clamped to 0-10, lists capped, and a correction is only kept when its
    `original` text really appears in the student's essay (so the UI never highlights invented quotes)."""
    d = extract_json(raw)
    out = {k: _score(d.get(k)) for k in SCORES}
    out["summary"] = str(d.get("summary", "")).strip()[:1000]
    out["strengths"] = _strings(d.get("strengths"), 4)
    out["improvements"] = _strings(d.get("improvements"), 5)
    corrections = []
    for c in (d.get("corrections") if isinstance(d.get("corrections"), list) else [])[:8]:
        if not isinstance(c, dict):
            continue
        original, suggestion = str(c.get("original", "")).strip(), str(c.get("suggestion", "")).strip()
        if original and suggestion and original in essay:
            corrections.append({"original": original[:200], "suggestion": suggestion[:200],
                                "reason": str(c.get("reason", "")).strip()[:300]})
    out["corrections"] = corrections
    if not out["summary"] and not out["improvements"]:
        raise ValueError("feedback has no content")
    return out
