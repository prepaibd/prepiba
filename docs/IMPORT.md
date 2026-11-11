# Importing exam data

`manage.py import_prepiba` loads `data/` into the catalog. It is idempotent (upserts on natural keys)
and each exam runs in its own transaction. Re-importing is safe for reviewer work: a question whose answer was set by a reviewer
(`answer_source=reviewer`) keeps its answer, status and correct option; a question whose Bangla is `reviewed` keeps its
Bangla stem, options and solution. Everything else is refreshed from `data/`.

## Answer resolution (`apps/catalog/answers.py`)
No source PDF prints an answer key. Each question has a legacy key (question JSON) and an independently
derived key (`data/sol`). Result per question:

| Status | Meaning | Scored? |
|---|---|---|
| verified | legacy key and derived solution agree | yes (MCQ only) |
| derived | only the derived solution has a key | yes (MCQ only) |
| unverified | only the legacy key, or no key | no |
| disputed | keys conflict, or the key is multi-valued ("A and B") | no |
| none | essay / argument, no key | no |

Questions with a `source_defect` are never scored. Free-response questions (no options) are stored with
`answer_kind=text` and are shown with their answer but not auto-scored.

Answer formats normalised on import: letter, option text, "A (50%)", "... (GMAT-style: C)".
Data-sufficiency questions get five options parsed from the group instruction.

`data/answer_flags.json` (from the solution notes) becomes `Question.review_note`; it does not change scoring.

## Known data issues left as-is
- 2020 Dec 3-34 references rule `cr-method`, which is not in `rules.json` (import warns and skips the link).
- Unicode math (e.g. `ab²c³d⁴`) is not converted to LaTeX.
- `Exam.duration_minutes` and `negative_mark` are unset: the source data does not state them.
