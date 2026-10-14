from django.db import models


class MediaAsset(models.Model):
    """A reusable image with its licence, served from our own storage."""

    commons_title = models.CharField(max_length=512, unique=True)
    file = models.CharField(max_length=256, help_text="Path under MEDIA_ROOT.")
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    author = models.CharField(max_length=512, blank=True)
    license = models.CharField(max_length=128)
    license_url = models.URLField(blank=True)
    source_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["commons_title"]

    def __str__(self):
        return self.commons_title

    @property
    def credit(self) -> str:
        author = self.author or "佚名"
        return f"{author} · {self.license} · 维基共享资源"
