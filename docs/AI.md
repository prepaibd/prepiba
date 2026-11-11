# AI tutor, writing feedback and Bangla review

## Providers (`apps/ai/provider.py`)
`AI_PROVIDER=mock` returns canned output (dev/tests). `AI_PROVIDER=gemini` uses google-genai with
`GEMINI_API_KEY` / `GEMINI_MODEL`. With no key the AI endpoints answer 503 instead of faking a reply.
Every call is bounded by `AI_TIMEOUT_SECONDS` (default 45). Transient upstream failures (5xx, 429) are retried
twice with short jittered backoff while the time budget allows; other errors fail immediately. A stream is only
retried before its first chunk reaches the student (a retry would repeat text they already saw). Preview models
(e.g. `gemini-3.x-flash-lite`) had real 5xx spikes and one ~85 s stall while this was built, so these limits matter.
The adapter is covered by tests against a fake SDK client and has been exercised live (streaming tutor and JSON
writing feedback). **Tests never call a live model**: `tests/conftest.py` forces the mock provider whatever `.env` says.

## Allowance (`apps/ai/quota.py`)
Daily limits per plan (settings `AI_DAILY_LIMITS`, env `AI_*_PER_DAY`), reset at local midnight (Asia/Dhaka).
The allowance is reserved under a row lock *before* the model is called and released if the call fails,
so errors never cost the student a message. `GET /api/v1/ai/usage/` reports what is left.

## Tutor (`apps/chat`)
`POST /chat/sessions/` (optionally `{question_id}`), `POST /chat/sessions/{id}/messages/` streams server-sent events
(`delta` ... `done` | `error`). Safety rules enforced in code and covered by tests:
- Student text is only ever a user message; it is never placed in the system prompt.
- Question-bank text is passed inside a delimited block labelled as data, not instructions.
- While a question is inside the student's *running* exam the tutor is told not to reveal the answer
  and the answer key and stored solution are not sent to the model at all.
- A failed call removes the unanswered user message and is not charged; a client disconnect keeps the partial reply.

## Writing feedback (`apps/writing`)
`GET /writing/prompts/` (26 past essay/argument tasks), `POST /writing/submissions/`, `POST .../{id}/retry/`.
Model output is untrusted: JSON is extracted, scores clamped to 0-10, lists capped, and any "correction" whose quoted
text is not actually in the essay is dropped. Unusable output gets one retry, then the submission is saved as
`failed` (text kept, not charged) and can be retried. Feedback is practice guidance, not an official mark.
Grading runs inside the request (a few seconds); move it to a worker if volume grows.

## Bangla review (`apps/review`)
Reviewers/admins (`User.role`) use `/review` in the web app or `GET/PATCH /api/v1/review/questions/`.
Edits are rejected unless numbers and `$..$` LaTeX match the English and no Bangla digits are used (the same rules as
`tools/check_bn.py`). Every change is written to `ReviewLog`. Editing a reviewed translation sends it back to draft.
Roles are set in the Django admin (`/admin/` -> Users).
