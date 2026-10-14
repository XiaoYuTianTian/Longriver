import json
from pathlib import Path

from django.core.management.base import BaseCommand, no_translations

from knowledge.models import Region, Topic

CONTENT = Path(__file__).resolve().parents[4] / "content"
GAZETTEERS = [CONTENT / "gazetteer.json", CONTENT / "gazetteer_wikidata.json"]

TOPICS = [
    ("politics", "政治"),
    ("economy", "经济"),
    ("society", "社会"),
    ("technology", "科技"),
    ("culture", "文化"),
]


def load_places() -> list[dict]:
    places = []
    for path in GAZETTEERS:
        if path.exists():
            places.extend(json.loads(path.read_text(encoding="utf-8"))["places"])
    return places


class Command(BaseCommand):
    help = "Load Changhe regions and timeline topics."

    @no_translations
    def handle(self, *args, **options):
        places = load_places()
        saved = {}
        for place in places:
            region, _ = Region.objects.update_or_create(
                slug=place["slug"],
                defaults={
                    "name": place["name"],
                    "sort_order": place["sort_order"],
                    "level": place.get("level", "region"),
                    "latitude": place.get("latitude"),
                    "longitude": place.get("longitude"),
                    "wikidata_id": place.get("wikidata") or "",
                    "description": place.get("description") or "",
                },
            )
            saved[place["slug"]] = region
        for place in places:
            parent = saved.get(place["parent"]) if place["parent"] else None
            region = saved[place["slug"]]
            if region.parent_id != (parent.id if parent else None):
                region.parent = parent
                region.save(update_fields=["parent"])
        for slug, name in TOPICS:
            Topic.objects.update_or_create(slug=slug, defaults={"name": name})
        self.stdout.write(self.style.SUCCESS(f"Reference data loaded: {len(places)} places."))
