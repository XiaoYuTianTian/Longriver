from django.core.management.base import BaseCommand, no_translations

from knowledge.models import Region, Topic

REGIONS = [
    ("east-asia", "东亚", 10),
    ("west-asia-north-africa", "西亚与北非", 20),
    ("europe", "欧洲", 30),
    ("americas", "美洲", 40),
]

TOPICS = [
    ("politics", "政治"),
    ("economy", "经济"),
    ("society", "社会"),
    ("technology", "科技"),
    ("culture", "文化"),
]


class Command(BaseCommand):
    help = "Load Changhe regions and timeline topics."

    @no_translations
    def handle(self, *args, **options):
        for slug, name, sort_order in REGIONS:
            Region.objects.update_or_create(
                slug=slug,
                defaults={"name": name, "parent": None, "sort_order": sort_order},
            )
        for slug, name in TOPICS:
            Topic.objects.update_or_create(slug=slug, defaults={"name": name})
        self.stdout.write(self.style.SUCCESS("Reference data loaded."))
