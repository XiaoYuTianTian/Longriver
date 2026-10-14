import json
from pathlib import Path

from django.core.management.base import BaseCommand, no_translations
from django.db import transaction

from knowledge.models import MediaAsset, Person, Region

CONTENT = Path(__file__).resolve().parents[4] / "content"


def read(name: str, default):
    path = CONTENT / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


class Command(BaseCommand):
    help = "Attach Wikidata people details, place summaries and licensed images."

    @no_translations
    @transaction.atomic
    def handle(self, *args, **options):
        manifest = read("media_manifest.json", {})
        summaries = read("wiki_summaries.json", {})
        people = read("wikidata_people.json", {"people": []})["people"]
        places = read("gazetteer_wikidata.json", {"places": []})["places"]

        assets = {}
        for title, entry in manifest.items():
            asset, _ = MediaAsset.objects.update_or_create(
                commons_title=title,
                defaults={
                    "file": entry["file"],
                    "width": entry["width"],
                    "height": entry["height"],
                    "author": entry["author"][:512],
                    "license": entry["license"][:128],
                    "license_url": entry["license_url"][:200],
                    "source_url": entry["source_url"][:200],
                },
            )
            assets[title] = asset

        regions = {region.slug: region for region in Region.objects.all()}
        updated_people = 0
        for entry in people:
            person, _ = Person.objects.get_or_create(wikidata_id=entry["qid"], defaults={"name": entry["name"]})
            person.name = entry["name"]
            person.birth_year = entry["birth_year"]
            person.death_year = entry["death_year"]
            person.description = summaries.get(entry.get("zhwiki") or "") or entry["description"] or ""
            person.primary_region = regions.get(entry["place_slug"])
            person.image = assets.get(entry.get("image") or "")
            person.save()
            updated_people += 1

        updated_places = 0
        for entry in places:
            region = regions.get(entry["slug"])
            if region is None:
                continue
            region.description = summaries.get(entry.get("zhwiki") or "") or entry.get("description") or ""
            region.image = assets.get(entry.get("image") or "")
            region.save(update_fields=["description", "image"])
            updated_places += 1

        self.stdout.write(self.style.SUCCESS(
            f"Loaded {len(assets)} images, {updated_people} people, {updated_places} places."
        ))
