import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError, no_translations

from knowledge.services.extraction import extract_candidates
from knowledge.services.importing import import_open_data


class Command(BaseCommand):
    help = "Import openly licensed historical JSON, or structured candidate text, as drafts."

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--candidates", action="store_true")
        parser.add_argument("--source-title", default="")
        parser.add_argument("--source-url", default="")

    @no_translations
    def handle(self, *args, **options):
        path = Path(options["path"])
        if path.suffix.lower() not in {".json", ".txt"}:
            raise CommandError("当前版本只接受 UTF-8 文本或 JSON，不接收图片。")
        if options["candidates"]:
            if not options["source_title"] or not options["source_url"]:
                raise CommandError("文本抽取需要 --source-title 和 --source-url。")
            payload = {
                "source": {
                    "title": options["source_title"],
                    "kind": "dataset",
                    "license_status": "metadata_only",
                    "canonical_url": options["source_url"],
                },
                "claims": extract_candidates(path.read_text(encoding="utf-8")),
            }
            result = import_open_data(payload, ai_generated=True)
        else:
            payload = json.loads(path.read_text(encoding="utf-8"))
            result = import_open_data(payload)
        self.stdout.write(
            self.style.SUCCESS(f"Imported {result.created} draft claims; skipped {result.skipped}.")
        )
