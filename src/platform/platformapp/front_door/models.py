from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page


class HomePage(Page):
    """Lane 1 home: body lives on the page row, not a template file."""

    body = RichTextField(blank=True)

    content_panels = [*Page.content_panels, FieldPanel("body")]
