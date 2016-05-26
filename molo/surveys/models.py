import json

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

from django.db.models.fields import TextField
from django.shortcuts import render
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

    def get_submission_class(self):
        return CustomFormSubmission

    def process_form_submission(self, form):
        self.get_submission_class().objects.create(
            form_data=json.dumps(form.cleaned_data, cls=DjangoJSONEncoder),
            page=self, user=form.user
        )

    def serve(self, request, *args, **kwargs):
        if self.get_submission_class().objects.filter(
            page=self, user__pk=request.user.pk
        ).exists():
            return render(
                request,
                self.template,
                self.get_context(request)
            )

        return super(SurveyPage, self).serve(request, *args, **kwargs)


class SurveyFormField(surveys_models.AbstractFormField):
    page = ParentalKey(SurveyPage, related_name='survey_form_fields')


class CustomFormSubmission(surveys_models.AbstractFormSubmission):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)

    class Meta:
        unique_together = ('page', 'user')
