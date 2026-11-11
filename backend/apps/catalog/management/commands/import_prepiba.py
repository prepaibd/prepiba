from pathlib import Path

from django.core.management.base import BaseCommand

from apps.catalog.importer import import_all


class Command(BaseCommand):
    help = "Import curated prepiba exam data (data/) into the catalog. Safe to re-run."

    def add_arguments(self, parser):
        parser.add_argument("--data-dir", help="Override settings.DATA_DIR")
        parser.add_argument("--exam", action="append", help="Import only this exam slug (repeatable)")

    def handle(self, *args, **opts):
        r = import_all(Path(opts["data_dir"]) if opts["data_dir"] else None, opts["exam"])
        out = self.stdout.write
        out(f"exams={r.exams} groups={r.groups} questions={r.questions} options={r.options} "
            f"figures={r.figures} solutions={r.solutions}")
        out(f"answer_status: {dict(sorted(r.status.items()))}")
        out(f"answer_kind:   {dict(sorted(r.kinds.items()))}")
        for w in r.warnings:
            self.stderr.write(f"WARNING {w}")
        out(f"warnings={len(r.warnings)}")
