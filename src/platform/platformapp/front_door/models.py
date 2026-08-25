from django.db import models
from django.utils import timezone
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page


class HomePage(Page):
    """Lane 1 home: body lives on the page row, not a template file."""

    body = RichTextField(blank=True)

    content_panels = [*Page.content_panels, FieldPanel("body")]


class ConsoleEditorialPage(Page):
    """CMS home for curated console narrative (inventory editorial_blocks)."""

    surface_id = models.CharField(max_length=64)
    body = RichTextField(blank=True)

    content_panels = [
        *Page.content_panels,
        FieldPanel("surface_id"),
        FieldPanel("body"),
    ]

    parent_page_types = ["front_door.HomePage"]


class DetectorVerdict(models.Model):
    """Cached detector result from the scheduled job, not a per-request run."""

    detector = models.CharField(max_length=64, unique=True)
    state = models.CharField(max_length=32)
    findings = models.PositiveIntegerField(default=0)
    verdict = models.TextField(blank=True)
    captured_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "detector_verdict"

    def __str__(self) -> str:
        return self.detector
