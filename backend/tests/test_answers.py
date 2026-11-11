from apps.catalog.answers import DS_FALLBACK, parse_ds_options, resolve_answer, to_label

OPTS = {"A": "x", "B": "y", "C": "z", "D": "w", "E": "v"}


def test_to_label_variants():
    assert to_label("C", OPTS) == "C"
    assert to_label("c", OPTS) == "C"
    assert to_label("A (50%)", OPTS) == "A"
    assert to_label("Statement (2) alone is sufficient (GMAT-style: B)", OPTS) == "B"
    assert to_label("Q", OPTS) is None
    assert to_label("Z", OPTS) == "C"  # matches the text of option C
    assert to_label("A and B", OPTS) is None
    assert to_label(None, OPTS) is None


def test_to_label_matches_option_text_case_insensitively():
    assert to_label("Y", {"A": "x", "B": "y"}) == "B"


def test_to_label_ambiguous_option_text_is_unmapped():
    assert to_label("tk. 300", {"A": "tk. 300", "B": "tk. 300"}) is None


def test_agreement_is_verified():
    r = resolve_answer("fill_blank", "E", "E", OPTS)
    assert (r.kind, r.correct_label, r.status) == ("mcq", "E", "verified")


def test_conflict_is_disputed_and_keeps_previous_key():
    r = resolve_answer("problem_solving", "C", "D", OPTS)
    assert (r.status, r.correct_label, r.prev) == ("disputed", "D", "C")


def test_solution_only_is_derived():
    assert resolve_answer("problem_solving", None, "A", OPTS).status == "derived"


def test_legacy_only_is_unverified():
    assert resolve_answer("problem_solving", "A", None, OPTS).status == "unverified"


def test_multi_answer_is_disputed_without_correct_option():
    r = resolve_answer("reading_comp", "A and B", "A and B", {"A": "p", "B": "q", "C": "r"})
    assert (r.status, r.correct_label, r.answer_text) == ("disputed", None, "A and B")


def test_missing_key_is_unverified():
    r = resolve_answer("error_identification", None, None, OPTS)
    assert (r.status, r.correct_label) == ("unverified", None)


def test_essay_and_keyless_argument_have_no_key():
    assert resolve_answer("essay", None, None, {}).status == "none"
    assert resolve_answer("argument", None, None, {}).kind == "essay"


def test_free_response_is_text_kind():
    r = resolve_answer("problem_solving", "1:1", "1:1", {})
    assert (r.kind, r.status, r.answer_text) == ("text", "verified", "1:1")
    assert resolve_answer("problem_solving", None, "6 pairs", {}).status == "derived"


def test_parse_ds_options_reads_instruction_or_falls_back():
    instr = "Intro\n" + "\n".join(f"{k}. {v}" for k, v in DS_FALLBACK.items())
    assert parse_ds_options(instr) == DS_FALLBACK
    assert parse_ds_options("no options here") == DS_FALLBACK
