from django.db.models.fields import TextField
from modelcluster.fields import ParentalKey
from molo.core.models import SectionPage, ArticlePage

from wagtail.wagtailadmin.edit_handlers import FieldPanel, InlinePanel

from wagtailsurveys import models as surveys_models


SectionPage.subpage_types += ['surveys.SurveyPage']
ArticlePage.subpage_types += ['surveys.SurveyPage']


class SurveyPage(surveys_models.AbstractSurvey):
    intro = TextField(blank=True)
    thank_you_text = TextField(blank=True)

    content_panels = surveys_models.AbstractSurvey.content_panels + [
        FieldPanel('intro', classname="full"),
        InlinePanel('survey_form_fields', label="Form fields"),
        FieldPanel('thank_you_text', classname="full"),
    ]


class SurveyFormField(surveys_models.AbstractFormField):
    page = ParentalKey(SurveyPage, related_name='survey_form_fields')
