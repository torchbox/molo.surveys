import json

from django.conf import settings
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models.fields import TextField, BooleanField
from django.shortcuts import render

from modelcluster.fields import ParentalKey

from molo.core.models import (
    SectionPage,
    ArticlePage,
    TranslatablePageMixin,
    PreventDeleteMixin,
)

from wagtail.wagtailcore.models import Page
from wagtail.wagtailadmin.edit_handlers import FieldPanel, InlinePanel, \
    MultiFieldPanel
from wagtailsurveys import models as surveys_models


# See docs: https://github.com/torchbox/wagtailsurveys

SectionPage.subpage_types += ['surveys.MoloSurveyPage']
ArticlePage.subpage_types += ['surveys.MoloSurveyPage']


class SurveysIndexPage(Page, PreventDeleteMixin):
    parent_page_types = []
    subpage_types = ['surveys.MoloSurveyPage']


class MoloSurveyPage(TranslatablePageMixin, surveys_models.AbstractSurvey):
    intro = TextField(blank=True)
    thank_you_text = TextField(blank=True)

    allow_anonymous_submissions = BooleanField(
        default=False,
        help_text='Check this to allow users who are NOT logged in to complete'
                  ' surveys.'
    )
    allow_multiple_submissions_per_user = BooleanField(
        default=False,
        help_text='Check this to allow users to complete a survey more than'
                  ' once.'
    )

    show_results = BooleanField(
        default=False,
        help_text='Whether to show the survey results to the user after they'
                  ' have submitted their answer(s).'
    )

    multi_step = BooleanField(
        default=False,
        verbose_name='Multi-step',
        help_text='Whether to display the survey questions to the user one at'
                  ' a time, instead of all at once.'
    )

    content_panels = surveys_models.AbstractSurvey.content_panels + [
        FieldPanel('intro', classname='full'),
        InlinePanel('survey_form_fields', label='Form fields'),
        FieldPanel('thank_you_text', classname='full'),
    ]

    settings_panels = surveys_models.AbstractSurvey.settings_panels + [
        MultiFieldPanel([
            FieldPanel('allow_anonymous_submissions'),
            FieldPanel('allow_multiple_submissions_per_user'),
            FieldPanel('show_results'),
            FieldPanel('multi_step')
        ], heading='Survey Settings')
    ]

    def get_context(self, request, *args, **kwargs):
        context = super(MoloSurveyPage, self).get_context(
            request, *args, **kwargs
        )

        # check request method so that results are shown only on the landing
        # page
        if self.show_results and request.method == 'POST':
            results = dict()
            # Get information about form fields
            data_fields = [
                (field.clean_name, field.label)
                for field in self.get_form_fields()
            ]

            # Get all submissions for current page
            submissions = self.get_submission_class().objects.filter(page=self)
            for submission in submissions:
                data = submission.get_data()

                # Count results for each question
                for name, label in data_fields:
                    answer = data.get(name)
                    if answer is None:
                        # Something wrong with data.
                        # Probably you have changed questions
                        # and now we are receiving answers for old questions.
                        # Just skip them.
                        continue

                    if type(answer) is list:
                        # answer is a list if the field type is 'Checkboxes'
                        answer = u', '.join(answer)

                    question_stats = results.get(label, {})
                    question_stats[answer] = question_stats.get(answer, 0) + 1
                    results[label] = question_stats

            context.update({
                'results': results,
            })

        return context

    def get_data_fields(self):
        data_fields = [
            ('username', 'Username'),
        ]
        data_fields += super(MoloSurveyPage, self).get_data_fields()
        return data_fields

    def get_submission_class(self):
        return MoloSurveySubmission

    def get_parent_section(self):
        return SectionPage.objects.all().ancestor_of(self).last()

    def process_form_submission(self, form):
        user = form.user if not form.user.is_anonymous() else None

        self.get_submission_class().objects.create(
            form_data=json.dumps(form.cleaned_data, cls=DjangoJSONEncoder),
            page=self, user=user
        )

    def has_user_submitted_survey(self, request, survey_page_id):
        if 'completed_surveys' not in request.session:
            request.session['completed_surveys'] = []

        if request.user.pk is not None \
            and self.get_submission_class().objects.filter(
                page=self, user__pk=request.user.pk
            ).exists() \
                or survey_page_id in request.session['completed_surveys']:
                    return True

        return False

    def set_survey_as_submitted_for_session(self, request):
        if 'completed_surveys' not in request.session:
            request.session['completed_surveys'] = []

        request.session['completed_surveys'].append(self.id)
        request.session.modified = True

    def get_form_class_for_step(self, step):
        return self.form_builder(step.object_list).get_form_class()

    def serve_multi_step(self, request):
        """
        Implements a simple multi-step form.

        Stores each step in the session.
        When the last step is submitted correctly, the whole form is saved in
        the DB.
        """
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
                survey_data = json.loads(
                    request.session.get(session_key_data, '{}'))
                survey_data.update(prev_form.cleaned_data)
                request.session[session_key_data] = json.dumps(
                    survey_data, cls=DjangoJSONEncoder)

                if prev_step.has_next():
                    # Create a new form for a following step, if the following
                    # step is present
                    form_class = self.get_form_class_for_step(step)
                    form = form_class(page=self, user=request.user)
                else:
                    # If there is no more steps, create form for all fields
                    form = self.get_form(
                        json.loads(request.session[session_key_data]),
                        page=self, user=request.user
                    )

                    if form.is_valid():
                        # Perform validation again for whole form.
                        # After successful validation, save data into DB,
                        # and remove from the session.
                        self.set_survey_as_submitted_for_session(request)

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
        context['is_intermediate_step'] = step.has_next()

        return render(
            request,
            self.template,
            context
        )

    def serve(self, request, *args, **kwargs):
        if not self.allow_multiple_submissions_per_user \
                and self.has_user_submitted_survey(request, self.id):
            return render(request, self.template, self.get_context(request))

        if self.multi_step:
            return self.serve_multi_step(request)

        if request.method == 'POST':
            form = self.get_form(request.POST, page=self, user=request.user)
            if form.is_valid():
                self.set_survey_as_submitted_for_session(request)

        return super(MoloSurveyPage, self).serve(request, *args, **kwargs)


class MoloSurveyFormField(surveys_models.AbstractFormField):
    page = ParentalKey(MoloSurveyPage, related_name='survey_form_fields')


class MoloSurveySubmission(surveys_models.AbstractFormSubmission):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True
    )

    def get_data(self):
        form_data = super(MoloSurveySubmission, self).get_data()
        form_data.update({
            'username': self.user.username if self.user else 'Anonymous',
        })
        return form_data
