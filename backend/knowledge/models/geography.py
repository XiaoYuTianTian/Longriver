from django.db import models


class Region(models.Model):
    name = models.CharField(max_length=128)
    slug = models.SlugField(max_length=128, unique=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Polity(models.Model):
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=160, unique=True)
    alternate_names = models.JSONField(default=list, blank=True)
    active_span = models.ForeignKey(
        "HistoricalTimeSpan",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="polities",
    )
    regions = models.ManyToManyField(Region, related_name="polities", blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "polities"

    def __str__(self):
        return self.name
