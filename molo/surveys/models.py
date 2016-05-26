import json

from django.conf import settings
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

from django.db.models.fields import TextField
from django.shortcuts import render
from modelcluster.fields import ParentalKey
from molo.core.models import SectionPage, ArticlePage

from wagtail.wagtailadmin.edit_handlers import FieldPanel, InlinePanel

from wagtailsurveys import models as surveys_models


# See docs: https://github.com/torchbox/wagtailsurveys

SectionPage.subpage_types += ['surveys.SurveyPage',
                              'surveys.MultiStepSurveyPage']
ArticlePage.subpage_types += ['surveys.SurveyPage',
                              'surveys.MultiStepSurveyPage']


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

    def has_user_submitted_survey(self, user_pk):
        if self.get_submission_class().objects.filter(
            page=self, user__pk=user_pk
        ).exists():
            return True

        return False

    def serve(self, request, *args, **kwargs):
        if self.has_user_submitted_survey(request.user.pk):
            return render(request, self.template, self.get_context(request))

        return super(SurveyPage, self).serve(request, *args, **kwargs)


class SurveyFormField(surveys_models.AbstractFormField):
    page = ParentalKey(SurveyPage, related_name='survey_form_fields')


class CustomFormSubmission(surveys_models.AbstractFormSubmission):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)

    class Meta:
        unique_together = ('page', 'user')


class MultiStepSurveyPage(SurveyPage):
    landing_page_template = 'surveys/survey_page_landing.html'

    class Meta:
        verbose_name = 'Survey Page (Multi-Step)'

    def get_form_class_for_step(self, step):
        return self.form_builder(step.object_list).get_form_class()

    def serve(self, request, *args, **kwargs):
        """
        Implements a simple multi-step form.

        Stores each step in the session.
        When the last step is submitted correctly, the whole form is saved in
        the DB.
        """

        if self.has_user_submitted_survey(request.user.pk):
            return render(request, self.template, self.get_context(request))

        session_key_data = 'survey_data-%s' % self.pk
        is_last_step = False
        step_number = request.GET.get('p', 1)

        paginator = Paginator(self.get_form_fields(), per_page=1)
        try:
            step = paginator.page(step_number)
        except PageNotAnInteger:
            step = paginator.page(1)
        except EmptyPage:
            step = paginator.page(paginator.num_pages)
            is_last_step = True

        if request.method == 'POST':
            # The first step will be submitted with step_number == 2,
            # so we need to get a from from previous step
            # Edge case - submission of the last step
            prev_step = step if is_last_step else paginator.page(
                step.previous_page_number())

            # Create a form only for submitted step
            prev_form_class = self.get_form_class_for_step(prev_step)
            prev_form = prev_form_class(request.POST, page=self,
                                        user=request.user)
            if prev_form.is_valid():
                # If data for step is valid, update the session
                survey_data = request.session.get(session_key_data, {})
                survey_data.update(prev_form.cleaned_data)
                request.session[session_key_data] = survey_data

                if prev_step.has_next():
                    # Create a new form for a following step, if the following
                    # step is present
                    form_class = self.get_form_class_for_step(step)
                    form = form_class(page=self, user=request.user)
                else:
                    # If there is no more steps, create form for all fields
                    form = self.get_form(
                        request.session[session_key_data],
                        page=self, user=request.user
                    )

                    if form.is_valid():
                        # Perform validation again for whole form.
                        # After successful validation, save data into DB,
                        # and remove from the session.
                        self.process_form_submission(form)
                        del request.session[session_key_data]

                        # Render the landing page
                        return render(
                            request,
                            self.landing_page_template,
                            self.get_context(request)
                        )
            else:
                # If data for step is invalid
                # we will need to display form again with errors,
                # so restore previous state.
                form = prev_form
                step = prev_step
        else:
            # Create empty form for non-POST requests
            form_class = self.get_form_class_for_step(step)
            form = form_class(page=self, user=request.user)

        context = self.get_context(request)
        context['form'] = form
        context['fields_step'] = step
        return render(
            request,
            self.template,
            context
        )
