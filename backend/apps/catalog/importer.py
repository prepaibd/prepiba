"""Import the curated prepiba data (data/) into the catalog tables.

Idempotent: every row is upserted on its natural key, so re-running changes nothing.
Each exam is imported inside its own transaction.
"""
import json
import re
import shutil
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils.text import slugify

from . import answers
from .models import (
    Exam,
    ExamSection,
    Figure,
    Formula,
    GrammarRule,
    Option,
    Question,
    QuestionGroup,
    Solution,
    Subject,
    Topic,
)

SUBJECTS = {
    "mathematics": ("Mathematics", "গণিত", 1),
    "language": ("Language & Communication", "ভাষা ও যোগাযোগ", 2),
    "analytical": ("Analytical Ability", "বিশ্লেষণধর্মী যোগ্যতা", 3),
    "writing": ("Writing", "লেখা", 4),
}
# TAXONOMY.md heading keyword -> subject slug
TAXONOMY_SUBJECT = {"math": "mathematics", "logic": "analytical", "language": "language", "writing": "writing"}
RC_SUBTOPICS = ["RC - Main Idea", "RC - Inference", "RC - Detail", "RC - Vocabulary", "RC - Tone & Purpose"]
MONTHS = {"jan": 1, "may": 5, "june": 6, "jul": 7, "dec": 12}
FULL_PAPER_MIN_QUESTIONS = 72


@dataclass
class Report:
    exams: int = 0
    groups: int = 0
    questions: int = 0
    options: int = 0
    figures: int = 0
    solutions: int = 0
    status: Counter = field(default_factory=Counter)
    kinds: Counter = field(default_factory=Counter)
    warnings: list = field(default_factory=list)

    def warn(self, msg):
        self.warnings.append(msg)


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def seed_subjects():
    out = {}
    for slug, (name, name_bn, order) in SUBJECTS.items():
        out[slug], _ = Subject.objects.update_or_create(
            slug=slug, defaults={"name": name, "name_bn": name_bn, "order": order}
        )
    return out


def parse_taxonomy(md: str) -> dict[str, list[str]]:
    """TAXONOMY.md -> {subject_slug: [topic names]} (names exactly as used in topics/*.json)."""
    result: dict[str, list[str]] = {}
    current = None
    for line in md.splitlines():
        if line.startswith("## "):
            head = line.lower()
            current = next((slug for key, slug in TAXONOMY_SUBJECT.items() if key in head), None)
            if current:
                result.setdefault(current, [])
        elif current and "|" in line:
            for name in (x.strip() for x in line.split("|")):
                if not name:
                    continue
                if name.startswith("Reading Comprehension"):
                    result[current] += ["Reading Comprehension", *RC_SUBTOPICS]
                else:
                    result[current].append(name)
    return result


def seed_topics(data_dir: Path, subjects):
    tax = parse_taxonomy((data_dir / "topics" / "TAXONOMY.md").read_text(encoding="utf-8"))
    by_name = {}
    for subj_slug, names in tax.items():
        for i, name in enumerate(names):
            topic, _ = Topic.objects.update_or_create(
                subject=subjects[subj_slug], slug=slugify(name)[:120] or f"topic-{i}",
                defaults={"name": name, "order": i},
            )
            by_name[name] = topic
    return by_name


def seed_learning(data_dir: Path):
    formulas = {}
    for slug, f in _load(data_dir / "formulas.json").items():
        formulas[slug], _ = Formula.objects.update_or_create(
            slug=slug,
            defaults={"title": f["title_en"], "title_bn": f.get("title_bn", ""), "body": f["body_en"],
                      "body_bn": f.get("body_bn", ""), "data": f},
        )
    rules = {}
    for slug, r in _load(data_dir / "rules.json").items():
        rules[slug], _ = GrammarRule.objects.update_or_create(
            slug=slug,
            defaults={"title": r["title_en"], "title_bn": r.get("title_bn", ""), "body": r["body_en"],
                      "body_bn": r.get("body_bn", ""), "data": r},
        )
    return formulas, rules


def _group_type(group: dict, qtypes: set[str]) -> str:
    if "data-sufficiency" in qtypes:
        return QuestionGroup.GroupType.DATA_SUFFICIENCY
    if "puzzle" in qtypes:
        return QuestionGroup.GroupType.PUZZLE
    if (group.get("stimulus") or {}).get("passage"):
        return QuestionGroup.GroupType.PASSAGE
    return QuestionGroup.GroupType.STANDALONE


def _exam_dates(slug: str):
    m = re.match(r"iba_mba_(\d{4})_(\w+)$", slug)
    if not m or m.group(2) not in MONTHS:
        raise ValueError(f"cannot derive year/month from exam slug {slug!r}")
    return int(m.group(1)), MONTHS[m.group(2)]


def import_exam(slug: str, data_dir: Path, subjects, topics, formulas, rules, report: Report):
    src = _load(data_dir / "questions" / f"{slug}.json")
    sol = _load(data_dir / "sol" / f"{slug}.sol.json")["items"]
    bn_doc = _load(data_dir / "bn" / f"{slug}.bn.json")
    bn, bn_groups = bn_doc["items"], bn_doc.get("groups", {})
    topic_map = _load(data_dir / "topics" / f"{slug}.json")
    flags = _load(data_dir / "answer_flags.json").get(slug, {})
    info = src["exam"]
    year, month = _exam_dates(slug)
    total_q = sum(len(g["questions"]) for p in src["parts"] for s in p["sections"] for g in s["groups"])
    marks = info.get("parts_marks") or {}

    with transaction.atomic():
        exam, _ = Exam.objects.update_or_create(
            slug=slug,
            defaults={
                "program": info["program"].lower(), "institute": info["institute"], "session": info["session"],
                "year": year, "month": month, "source_pdf": info.get("source_pdf", ""),
                "total_marks": sum(marks.values()) if marks and None not in marks.values() else None,
                "parts_marks": marks,
                "completeness": (Exam.Completeness.FULL if total_q >= FULL_PAPER_MIN_QUESTIONS
                                 else Exam.Completeness.PARTIAL),
                "unresolved_notes": src.get("unresolved", []),
            },
        )
        report.exams += 1
        for part in src["parts"]:
            for sec in part["sections"]:
                section, _ = ExamSection.objects.update_or_create(
                    exam=exam, section_no=sec["section_no"],
                    defaults={"part_label": part["part_label"], "subject": subjects[sec["subject"]],
                              "label": sec.get("source_section_label", ""), "order": sec["section_no"]},
                )
                q_order = 0
                for g_order, g in enumerate(sec["groups"]):
                    first = g["questions"][0]["number"]
                    gbn = bn_groups.get(f"{sec['section_no']}-{first}", {})
                    stim = g.get("stimulus") or {}
                    qtypes = {q["question_type"] for q in g["questions"]}
                    group, _ = QuestionGroup.objects.update_or_create(
                        section=section, order=g_order,
                        defaults={
                            "group_type": _group_type(g, qtypes), "source_label": g.get("source_group_label") or "",
                            "instruction": g.get("instruction") or "", "instruction_bn": gbn.get("instruction_bn", ""),
                            "passage": stim.get("passage") or "", "passage_bn": gbn.get("passage_bn", ""),
                            "table": stim.get("table"),
                        },
                    )
                    report.groups += 1
                    ds_options = answers.parse_ds_options(group.instruction)
                    for q in g["questions"]:
                        q_order += 1
                        _import_question(q, sec, section, group, q_order, ds_options, sol, bn, topic_map, topics,
                                         flags, formulas, rules, data_dir, slug, report)


def _import_question(q, sec, section, group, order, ds_options, sol, bn, topic_map, topics, flags, formulas, rules,
                     data_dir, exam_slug, report):
    key = f"{sec['section_no']}-{q['number']}"
    qtype = q["question_type"].replace("-", "_")
    if qtype not in Question.Type.values:
        raise ValueError(f"{exam_slug} {key}: unknown question type {q['question_type']!r}")

    options = {}
    printed = {}
    for o in q["options"]:
        label = o["label"].upper()
        options[label] = o["text"]
        printed[label] = o.get("label_display") or (o["label"] if o["label"] != label else "")
    if qtype == "data_sufficiency" and not options:
        options = dict(ds_options)

    s = sol.get(key, {})
    res = answers.resolve_answer(qtype, q.get("answer"), s.get("answer"), options)
    b = bn.get(key, {})
    topic_name = topic_map.get(key)
    topic = topics.get(topic_name)
    if topic_name and topic is None:
        report.warn(f"{exam_slug} {key}: topic {topic_name!r} not in taxonomy")

    stem = re.sub(rf"^\s*{q['number']}\.\s*", "", q["stem"], count=1)
    defaults = {
        "group": group, "order": order, "type": qtype, "stem": stem, "stem_bn": b.get("stem_bn", ""),
        "bn_status": b.get("bn_status", ""), "topic": topic,
        "marks": q.get("marks"), "answer_kind": res.kind, "answer_text": res.answer_text,
        "answer_status": res.status, "answer_source": res.source, "answer_prev": res.prev,
        "source_defect": q.get("source_defect") or "", "review_note": flags.get(key, ""),
    }
    # Never overwrite a human reviewer's decisions with the source data.
    existing = Question.objects.filter(section=section, number=q["number"]).first()
    keep_answer = bool(existing and existing.answer_source == "reviewer")
    keep_bn = bool(existing and existing.bn_status == "reviewed")
    if keep_answer:
        for f in ("answer_kind", "answer_text", "answer_status", "answer_source", "answer_prev"):
            defaults.pop(f)
    if keep_bn:
        defaults.pop("stem_bn")
        defaults.pop("bn_status")
    question, _ = Question.objects.update_or_create(section=section, number=q["number"], defaults=defaults)
    report.questions += 1
    report.status[question.answer_status] += 1
    report.kinds[question.answer_kind] += 1

    for i, (label, text) in enumerate(options.items()):
        opt_defaults = {"text": text, "text_bn": (b.get("options_bn") or {}).get(label, ""),
                        "label_display": printed.get(label, ""), "order": i, "is_correct": label == res.correct_label}
        if keep_answer:
            opt_defaults.pop("is_correct")
        if keep_bn:
            opt_defaults.pop("text_bn")
        Option.objects.update_or_create(question=question, label=label, defaults=opt_defaults)
        report.options += 1
    question.options.exclude(label__in=options.keys()).delete()

    for i, img in enumerate(q.get("images") or []):
        dest = _copy_figure(data_dir, exam_slug, img["path"])
        Figure.objects.update_or_create(
            question=question, fig_id=img["fig_id"],
            defaults={"role": img.get("role", "question"), "image": dest, "caption": img.get("caption", ""),
                      "order": i},
        )
        report.figures += 1

    if s:
        sol_defaults = {
            "body_en": s.get("en", ""), "body_bn": s.get("bn", ""),
            "trap_en": (s.get("trap") or {}).get("en", ""), "trap_bn": (s.get("trap") or {}).get("bn", ""),
            "trick_en": (s.get("trick") or {}).get("en", ""), "trick_bn": (s.get("trick") or {}).get("bn", ""),
            "note": s.get("note", ""),
        }
        if keep_bn:
            for f in ("body_bn", "trap_bn", "trick_bn"):
                sol_defaults.pop(f)
        solution, _ = Solution.objects.update_or_create(question=question, defaults=sol_defaults)
        solution.formulas.set([formulas[i] for i in s.get("formula_ids", []) if i in formulas])
        solution.rules.set([rules[i] for i in s.get("rule_ids", []) if i in rules])
        for i in s.get("formula_ids", []):
            if i not in formulas:
                report.warn(f"{exam_slug} {key}: unknown formula id {i!r}")
        for i in s.get("rule_ids", []):
            if i not in rules:
                report.warn(f"{exam_slug} {key}: unknown rule id {i!r}")
        report.solutions += 1


def _copy_figure(data_dir: Path, exam_slug: str, rel_path: str) -> str:
    source = data_dir / "questions" / exam_slug / rel_path
    dest_rel = f"figures/{exam_slug}/{Path(rel_path).name}"
    dest = Path(settings.MEDIA_ROOT) / dest_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        raise FileNotFoundError(f"figure missing: {source}")
    if not dest.exists() or dest.stat().st_size != source.stat().st_size:
        shutil.copyfile(source, dest)
    return dest_rel


def import_all(data_dir: Path | None = None, only: list[str] | None = None) -> Report:
    data_dir = Path(data_dir or settings.DATA_DIR)
    report = Report()
    with transaction.atomic():
        subjects = seed_subjects()
        topics = seed_topics(data_dir, subjects)
        formulas, rules = seed_learning(data_dir)
    slugs = only or sorted(p.stem for p in (data_dir / "questions").glob("*.json"))
    for slug in slugs:
        import_exam(slug, data_dir, subjects, topics, formulas, rules, report)
    return report
