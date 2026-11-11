# Bangla + English layer: how it is organised

English is the exam language. Bangla is an opt-in aid, shown after the English. The audited English text in `data/questions/` is never edited by this layer.

## What exists

| Layer | Files | Coverage |
|---|---|---|
| Bangla question help | `data/bn/<exam>.bn.json` (built from `data/bn_src/<exam>.py`) | All 493 math, data-sufficiency, puzzle and critical-reasoning questions in 14 exams, plus their group instructions and passages, and prose options |
| Solutions (EN + BN) | `data/sol/<exam>.sol.json` (built from `data/sol_src/`) | All 741 questions. Math/logic: steps, formula cards, traps. Language: rule + why wrong options fail. Writing: outline, phrases, mistakes |
| Formula cards | `data/formulas.json` (22) | Linked from math/logic solutions |
| Grammar rule library | `data/rules.json` (built from `data/rules_src.py`, 26) | Linked from language and writing solutions |
| Glossary + style guide | `data/glossary_bn.json`, `docs/BANGLA_STYLE_GUIDE.md` | Term choices and fidelity rules |

Grammar, vocabulary, reading comprehension and writing prompts are not translated (translating them would defeat the test). Bangla appears only inside their explanations.

## Rebuild

```
python3 scripts/make_bn.py <exam>      # assemble Bangla stems and check them
python3 scripts/make_sol.py <exam>     # assemble solutions
python3 scripts/make_rules.py          # grammar rules
python3 scripts/build.py               # bundle everything into viewer/data.js
python3 scripts/check_bn.py data/bn/<exam>.bn.json
python3 scripts/diff_answers.py        # derived answers vs stored answers
```

`check_bn.py` verifies that every number, variable and `$…$` expression in the Bangla equals the English, that no Bangla digits are used, and that every math/logic question and puzzle passage is covered. All 14 files pass.

## Answers

Answers were re-derived independently from the printed question (puzzles were checked by brute force in code). The viewer shows the derived answer and a "key updated" tag where it differs from the old key. The derived answer agrees with the old key for 735 of 741 questions. The differences:

| Exam | Question | Old key | Derived | Why |
|---|---|---|---|---|
| 2015 June | 2-33 | C (37) | D (41) | Printed sequence is 2, 5, 10, 17, **28**, z; differences are consecutive primes, so 41. If the "28" is a misprint for 26, the answer is 37 |
| 2015 June | 2-59 | C | E | As printed m and n may be negative, so m + n has two values; with positive m, n it would be C |
| 2016 June | 2-50 | none | A | 8/125 |
| 2018 May | 2-56 | none | C | Chair H is always a woman |
| 2016 June | 2-58, 2020 Dec 1-23 | text | letter | Same answer, written as a letter |

Items where the printed question is broken or needs an assumption are listed in `docs/SOLUTION_NOTES.md`.

## Status flags

Everything Bangla and every solution is Claude-written and marked `derived` / `draft`. Nothing is marked `reviewed` until a Bangla-native tutor or you check it.

## Not covered

- No Bangla translation of language-section stems, by design.
- A few source-garbled questions keep the old key and a note instead of a new one (2015 Dec 2-56, 2020 Dec 1-22, 2022 Dec 2-3, 2023 Dec 1-9).
