# SCOPE UPDATE 2026-11-05 (user decision; overrides ANSWER POLICY and Step 2 "Answer" bullet below)
Answers and explanations are OUT OF SCOPE for this audit. The user will regenerate them later.
- Do not re-solve, tag (`answer_source`/`answer_basis`) or change answers/explanations. Stored values stay as they are (known unreliable).
- The one exception already made: 2020 Dec Q22 answer set to null because the printed question is broken.
- Audit scope = printed content only: structure, passages/stimuli, stems, options (count/order/label/text), tables, math/$, symbols (`label_display`), images, page numbers.
- A question whose printed content is broken keeps the printed text and gets `source_defect`.
- Validator: answer/provenance checks are informational only, not blocking.
- Stale `unresolved` notes that talk about answers/keys are replaced by accurate printed-content notes (old text logged).
- The user authorised me to add or modify rules when needed; every rule change is recorded in this section.

# Plan: Verify every exam JSON against its source PDF

## ZERO-GUESS POLICY (overrides everything below)
The PDF is the only source. No guessed, inferred, "corrected" or reconstructed text, numbers, clues, options or labels.

1. **Transcribe, never repair.** Stems, options, passages, tables, clues are stored exactly as printed, including source typos, errors and contradictions. I never reword a question to make it solvable.
2. **Unreadable means flagged, not filled.** If a character, word or cell cannot be read with certainty at 300 dpi zoom, store the placeholder `[unreadable]`, set `source_defect`, and list it for the user to check against the original paper. No filling from context or memory.
3. **Source defects are recorded, not fixed.** If the printed question is broken (missing definition, contradictory statements, no valid answer), the stem stays as printed and a `source_defect` note says what is wrong. Any answer then is marked `answer_basis: "assumption"` with the assumption written separately, or left null if the user prefers. The assumption never edits the stem.
4. **Source vs. derived are separate.** Printed content (stem/options/stimulus/table) is one layer; answers and explanations are derived and tagged as such. Derived content must never leak into printed fields.
5. **Traceability.** Every question's log row records PDF page number (and region for tables/figures). A reader can open that page and compare.
6. **Two blind transcriptions.** Each exam is transcribed twice independently from fresh crops (second pass without seeing the first or the JSON), then diffed against the JSON. Every difference is resolved by looking at the zoomed crop, never by choosing the likelier reading.
7. **Character-level check** for numbers, names, units and symbols (digit-by-digit).
8. **Nothing is "close enough".** Any difference in any character counts as a discrepancy and is logged.
9. **Uncertainty report.** At sign-off, each exam lists every item I was not 100% sure about; the user gets that list rather than a silent best guess.

### Existing edits that deviated from or went beyond the printed source (to be re-audited first)
These were made earlier by me on a "best reading" basis and must each be reverted to the printed text or confirmed by the user against the original paper:
- 2018 May puzzle: "Manufacturing" changed to "Marketing".
- 2017 Dec couples puzzle: added clue "Riyad did not marry Lima".
- 2017 Jun Q61: answer relies on reading "do not serve" as "serve".
- 2016 Dec Q75: answer relies on reading "three fruits" as "two of the three".
- 2015 Dec Q56: z read as the average of x, y, y-1 (definition lost on page).
- 2015 Dec Q44, Q64; 2016 Jun Q58: answers chosen between multiple valid/contradictory outcomes.
- 2021 Q14-16, 2022 Q3 group ("from the last" interpretation), 2024 Q23/Q24/Q40, 2025 Q29: interpretation-based answers.
- 2020 Dec Q14-24 and the puzzle passage: taken from the user's photo (the only source); re-verify against the photo character by character.
- Every explanation and answer: re-derived from the printed text only.

## ANSWER POLICY (decided by the user)
The user will not supply answers or solutions. Most PDFs have no answer key; some (e.g. 2023 Dec) print a solution section.
1. **Provenance first.** View every page of all 14 PDFs and record per exam whether an answer key/solution is printed and on which pages. Tag every answer/explanation `answer_source`: `pdf_printed` (copied exactly) or `derived` (computed by me from the printed question).
2. **Derived answers stay** in the JSON, labelled `derived`. Re-solve each one independently from the printed question only (no peeking at the stored answer), compare, and fix if different.
3. **Printed solutions win.** If a PDF prints a solution that disagrees with my derived answer, keep the printed one and log the disagreement.
4. **Broken questions:** keep the printed stem, keep a derived answer labelled `answer_basis: "assumption"` with the assumption stated separately; never edit the stem to fit.
5. **Modification report is mandatory.** Every change to any JSON field (text, option, table, answer, explanation, flag) is appended to `docs/verification/<exam>.md` and to `docs/verification/CHANGELOG.md` as: exam | question | field | old value | new value | reason | evidence (PDF page). No change is made without a log entry; the old value is never lost.

## Context
The 14 exam JSONs in `data/questions/` were produced from scanned PDFs (`data/source_pdf/`) by OCR plus manual patching. Review flags are cleared, but flags are not proof of accuracy. Tables, `$`, LaTeX, and symbol labels (replacing I/II/III and A/B/C) were handled inconsistently. Goal: a repeatable, per-exam audit so that each JSON matches its PDF exactly (the PDF is the only source of truth). This plan will be saved as `docs/VERIFICATION_PLAN.md` (the project already has an empty `docs/` dir; `/doc` does not exist).

## Deliverable on approval
1. Copy this plan to `/Users/mdsayeddelowar/Desktop/prepiba/docs/VERIFICATION_PLAN.md`.
2. Create `docs/verification/` with one checklist/log file per exam (`<exam>.md`) and a `STATUS.md` tracker (exam, status, date, discrepancies found/fixed).
3. No JSON edits until the user approves starting the audit of the first exam.

## Scope and order
14 exams: 2015 June/Dec, 2016 June/Dec, 2017 June/Dec, 2018 May, 2019 Dec, 2020 Dec, 2021–2025 Dec. Audit one exam at a time, fully finished and signed off before the next. Start with the most-patched ones (2020 Dec, 2015 Dec, 2017 Jun), then the rest chronologically.

## Per-exam procedure (steps)
**Step 0 – Prepare**
- Render PDF pages to images at ≥150 dpi (`pdftoppm -jpeg`); use PyMuPDF clips at 300 dpi for tables, formulas, and tiny text.
- Dump the JSON to a flat, page-ordered list (reuse scratchpad `show.py` idea) so each question can be compared side by side with its page image.
- Note section/part structure and the expected question count from the PDF cover/instructions.

**Step 1 – Structural check**
- Question count and numbering per section equal the PDF; no gaps, duplicates, or misplaced numbers (2020 Dec missing page is the known case; its photo is `images/1.jpg`).
- Each question sits in the right group/passage and section; `source_group_label` and `instruction` match the printed text; marks (if any) match.
- Shared passages/stimuli are attached to every question that uses them, exactly once.

**Step 2 – Per-question text check (every question, no sampling)**
For each question compare against the page image:
- Stem: verbatim wording, punctuation, capitalisation, numbers, units, names. No OCR artefacts (merged words, `l`/`1`/`I`, `O`/`0`, dropped lines).
- Options: count, order, label, and text verbatim; none lost or merged.
- Answer: recompute independently from the printed question; compare with the stored answer and explanation (the PDF has no key; the answer must follow from the question as printed). Where the source is broken, keep the best reading and record the assumption in `unresolved` / notes.
- Images/diagrams: referenced file exists, is the correct crop, and is legible.

**Step 3 – Special-format rules (must match the source)**
1. **Tables**: any table in the source is stored as structured `table.rows` (not flattened text); same cell text, row/column count, merged cells (use `rowspan_first_col` or an extended merge flag), header row. Check it renders in the viewer (`viewer/index.html` table block) as in the PDF. Group-level tables go in `stimulus.table`; question-level in `q.table`.
2. **Dollar signs / currency**: money `$` stored as `$\$$` in KaTeX-rendered text so it is never read as a math delimiter; verify no stray `$` pair swallows text (search every text field for an odd or unescaped `$`). Check other currency (Tk, ৳, %, £) preserved.
3. **LaTeX / math**: any formula, fraction, exponent, root, subscript, inequality, or Greek letter is in valid LaTeX inside `$...$`; plain-text numbers stay plain. Check every math string parses in KaTeX (scripted render test, no `ParseError`), and visually matches the PDF (superscripts, fractions, bar/overline, ≤ ≥ ≠, ×, ÷, √, π).
4. **Symbol labels (replacing I/II/III and A/B/C)**: where the source uses symbols (e.g. ●, ■, ▲, ★, ①, (i), a)) instead of letters or roman numerals:
   - Decision to record in each log: keep the printed symbol in the displayed text; store `label` as the canonical letter (A–E) or roman numeral used for answer keying, and add a `label_display` field with the exact printed marker. Statements keyed "I, II, III" or "(i)(ii)(iii)" keep that exact marker in the text, and options like "I and II only" remain consistent with the markers used.
   - Build a one-time inventory (script scanning all 14 JSONs + PDFs) of every non-standard marker, then apply the one convention uniformly across all exams, and update the viewer to show `label_display` when present.
   - Verify answer letters still map to the right option after normalisation.
5. **Special characters**: fractions (½, ¼), degree, primes, en/em dashes, quotation marks, subscripts, and arrows compared char by char.
6. **Data sufficiency / no-option items**: statements (1), (2) text, standard A–E options reproduced consistently, or `options: []` with a documented rule.
7. **Passages and logic puzzles**: every clue present, in order, nothing dropped (2017 Dec and 2018 May were already found with missing or misread clues). Count clues against the PDF.
8. **Math/Word problem numbers**: every figure compared digit by digit (most common OCR error).

**Step 4 – Fix**
- Edit via a patch script per exam (reuse scratchpad `patch.py` pattern: set fields by "sec-num"); keep a before/after diff in the exam log.
- Update `data/topics/<exam>.json` only if the question set changes.
- Rebuild with `python3 scripts/build.py`.

**Step 5 – Automated checks (run after each exam, and across all exams at the end)**
Write `scripts/validate.py` (to be created on approval) that checks:
- JSON schema: required fields, option labels unique and in order, answer ∈ option labels (or documented no-option), numbering contiguous.
- Escaping: unescaped money `$`, odd count of `$`, `\(`/`\)` balance.
- KaTeX parse of every math span (node + katex, or headless render).
- Tables: rectangular rows, no empty header cell except merged ones.
- Stale artefacts: double spaces, stray `|`, `¦`, control characters, `needs_review` true, non-empty `unresolved` listed for the log.
- Images: referenced files exist.
- Topics: every question has a topic row (build reports 0 untagged).

**Step 6 – Visual verification in the viewer**
- Open each exam in the viewer; for every question with a table, math, symbols, or image, compare the rendered screen with the PDF page side by side. Screenshot mismatches into the log.

**Step 7 – Second-pass independent review**
- Re-read the full exam a second time from a fresh render, comparing only against the PDF, not against the first pass notes. Spot-check 100% of tables/math/symbol questions and 25% random plain questions; any new error means a full re-pass of that section.

**Step 8 – Sign-off**
- Exam log lists: counts verified, discrepancies found and fixed, remaining judgment-call items (with reasoning), reviewer date. `STATUS.md` marked "verified". Only then move on.

## Log template (per exam, `docs/verification/<exam>.md`)
Header (PDF, pages, expected count) → structure checklist → table of every question (number | stem ✔ | options ✔ | answer ✔ | table ✔ | math/$ ✔ | symbols ✔ | image ✔ | notes) → fixes diff → judgment calls → sign-off.

## Cross-exam consistency (final pass)
- One convention for symbol labels, tables, money, and math across all 14 exams (script-enforced).
- Regenerate viewer data; verify total row count (currently 738, plus any recovered questions) and 0 untagged.

## Critical files
- `data/questions/*.json`, `data/source_pdf/*.pdf`, `data/topics/*.json`
- `scripts/build.py` (rebuild), new `scripts/validate.py`
- `viewer/index.html` (table block, label rendering), `viewer/data.js`, `viewer/analysis_data.js` (generated)
- Docs: `docs/VERIFICATION_PLAN.md`, `docs/verification/*.md`

## End-to-end verification
1. `python3 scripts/validate.py` exits 0 on all exams.
2. `python3 scripts/build.py` reports expected row count and 0 untagged.
3. Viewer spot check of table, `$`, math, and symbol-label questions in each exam against the PDF.
4. `STATUS.md` shows all 14 exams verified with second-pass sign-off.

## Open decision (default chosen unless user says otherwise)
Symbol labels: keep printed symbol for display (`label_display`), canonical A–E/roman for keying.
