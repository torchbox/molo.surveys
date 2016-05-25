from modelcluster.fields import ParentalKey
from molo.core.models import LanguagePage, SectionPage, ArticlePage

from wagtail.wagtailadmin.edit_handlers import FieldPanel, InlinePanel
from wagtail.wagtailcore.fields import RichTextField

from wagtailsurveys import models as surveys_models


LanguagePage.subpage_types += ['surveys.SurveyPage']
SectionPage.subpage_types += ['surveys.SurveyPage']
ArticlePage.subpage_types += ['surveys.SurveyPage']


class SurveyPage(surveys_models.AbstractSurvey):
    intro = RichTextField(blank=True)
    thank_you_text = RichTextField(blank=True)

    content_panels = surveys_models.AbstractSurvey.content_panels + [
        FieldPanel('intro', classname="full"),
        InlinePanel('survey_form_fields', label="Form fields"),
        FieldPanel('thank_you_text', classname="full"),
    ]


class SurveyFormField(surveys_models.AbstractFormField):
    page = ParentalKey(SurveyPage, related_name='survey_form_fields')
