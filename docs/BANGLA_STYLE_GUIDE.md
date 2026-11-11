# Bangla style guide (draft v0.1 — for your review)

Purpose: Bangla is a scaffold for an English-only exam. English is always shown first; Bangla is opt-in.

## Scope (which questions get Bangla)
- Translate stems: mathematics, data-sufficiency, puzzles, critical-reasoning.
- Do NOT translate: grammar, vocabulary, reading-comprehension, writing prompts. Bangla appears only inside explanations.

## Fidelity rules (question translation)
1. Translate what is printed, nothing more. If the printed question is broken/ambiguous, the Bangla is equally ambiguous; add a note in `notes`, never repair it.
2. Never change numbers, variables, units, symbols or LaTeX. They must match the English exactly (checked by `scripts/check_bn.py`).
3. Use English digits (0-9), not Bangla digits (০-৯). Matches the exam and keeps the checker exact.
4. Variable names stay Latin (x, y, R, T). Names of people/places stay English.
5. Plain, spoken-register Bangla (চলিত ভাষা), short sentences. No sadhu forms. Instructions use the polite imperative (করুন, নির্ণয় করুন).

## Terms
- Translate common maths words (see `data/glossary_bn.json`, group `translate`): অনুপাত, গড়, ক্ষেত্রফল, ব্যাসার্ধ, ...
- Keep English for terms students must recognise on the paper (group `keep_english`): percentage, probability, integer, ratio when part of a label like "ratio 4:2:3" may be either; follow the glossary. Where a Bangla term is used for the first time in a question, optionally give English in brackets: বিভাজ্য (divisible).

## Solutions (later phase)
- EN: concise exam-style English.
- BN: Bangla script mixed with English technical terms, teacher-like tone. Not word-for-word. Math in LaTeX, English digits.
- Language questions: explain the rule in Bangla, keep English example sentences untouched.

## Status flags
`bn_status`: `draft` (written by Claude) -> `reviewed` (checked by you / a Bangla-native tutor). Nothing is `reviewed` automatically.
