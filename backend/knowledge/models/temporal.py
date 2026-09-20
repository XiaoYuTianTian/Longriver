from django.db import models
from django.db.models import F, Q

from .enums import CalendarSystem, TimePrecision


class HistoricalTimeSpan(models.Model):
    start_year = models.IntegerField(
        help_text="Signed proleptic year; 0 represents 1 BCE."
    )
    end_year = models.IntegerField(
        help_text="Inclusive signed proleptic year; 0 represents 1 BCE."
    )
    precision = models.CharField(
        max_length=16,
        choices=TimePrecision.choices,
        default=TimePrecision.YEAR,
    )
    calendar = models.CharField(
        max_length=16,
        choices=CalendarSystem.choices,
        default=CalendarSystem.GREGORIAN,
    )
    display_text = models.CharField(max_length=128)

    class Meta:
        ordering = ["start_year", "end_year", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(start_year__lte=F("end_year")),
                name="knowledge_timespan_start_lte_end",
            )
        ]

    def __str__(self):
        return self.display_text
