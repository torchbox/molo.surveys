import json

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.paginator import EmptyPage, PageNotAnInteger
from django.core.serializers.json import DjangoJSONEncoder
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Q
from django.db.models.fields import BooleanField, TextField
from django.dispatch import receiver
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from modelcluster.fields import ParentalKey
from molo.core.blocks import MarkDownBlock
from molo.core.models import (
    ArticlePage,
    FooterPage,
    Main,
    PreventDeleteMixin,
    SectionPage,
    TranslatablePageMixinNotRoutable,
    index_pages_after_copy,
)
from molo.core.utils import generate_slug
from wagtail.wagtailadmin.edit_handlers import (
    FieldPanel,
    FieldRowPanel,
    InlinePanel,
    MultiFieldPanel,
    PageChooserPanel,
    StreamFieldPanel,
)
from wagtail.wagtailcore import blocks
from wagtail.wagtailcore.fields import StreamField
from wagtail.wagtailcore.models import Orderable, Page
from wagtail.wagtailimages.blocks import ImageChooserBlock
from wagtail.wagtailimages.edit_handlers import ImageChooserPanel
from wagtail_personalisation.adapters import get_segment_adapter
from wagtailsurveys import models as surveys_models
from wagtailsurveys.models import AbstractFormField

from .blocks import SkipLogicField, SkipState, SkipLogicStreamPanel
from .forms import MoloSurveyForm, PersonalisableMoloSurveyForm
from .rules import ArticleTagRule, GroupMembershipRule, SurveySubmissionDataRule  # noqa
from .utils import SkipLogicPaginator


SKIP = 'NA (Skipped)'


# See docs: https://github.com/torchbox/wagtailsurveys
SectionPage.subpage_types += ['surveys.MoloSurveyPage']
ArticlePage.subpage_types += ['surveys.MoloSurveyPage']
FooterPage.parent_page_types += ['surveys.TermsAndConditionsIndexPage']


class TermsAndConditionsIndexPage(TranslatablePageMixinNotRoutable, Page):
    parent_page_types = ['surveys.SurveysIndexPage']
    subpage_types = ['core.Footerpage']


class SurveysIndexPage(Page, PreventDeleteMixin):
    parent_page_types = ['core.Main']
    subpage_types = [
        'surveys.MoloSurveyPage', 'surveys.PersonalisableSurvey',
        'surveys.TermsAndConditionsIndexPage']

    def copy(self, *args, **kwargs):
        site = kwargs['to'].get_site()
        main = site.root_page
        SurveysIndexPage.objects.child_of(main).delete()
        super(SurveysIndexPage, self).copy(*args, **kwargs)


@receiver(index_pages_after_copy, sender=Main)
def create_survey_index_pages(sender, instance, **kwargs):
    if not instance.get_children().filter(
            title='Surveys').exists():
        survey_index = SurveysIndexPage(
            title='Surveys', slug=('surveys-%s' % (
                generate_slug(instance.title), )))
        instance.add_child(instance=survey_index)
        survey_index.save_revision().publish()


class MoloSurveyPage(
        TranslatablePageMixinNotRoutable, surveys_models.AbstractSurvey):
    parent_page_types = [
        'surveys.SurveysIndexPage', 'core.SectionPage', 'core.ArticlePage']
    subpage_types = []

    base_form_class = MoloSurveyForm

    intro = TextField(blank=True)
    image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )
    content = StreamField([
        ('heading', blocks.CharBlock(classname="full title")),
        ('paragraph', MarkDownBlock()),
        ('image', ImageChooserBlock()),
        ('list', blocks.ListBlock(blocks.CharBlock(label="Item"))),
        ('numbered_list', blocks.ListBlock(blocks.CharBlock(label="Item"))),
        ('page', blocks.PageChooserBlock()),
    ], null=True, blank=True)
    thank_you_text = TextField(blank=True)
    submit_text = TextField(blank=True)
    homepage_button_text = TextField(blank=True)
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
    show_results_as_percentage = BooleanField(
        default=False,
        help_text='Whether to show the survey results to the user after they'
                  ' have submitted their answer(s) as a percentage or as'
                  ' a number.'
    )

    multi_step = BooleanField(
        default=False,
        verbose_name='Multi-step',
        help_text='Whether to display the survey questions to the user one at'
                  ' a time, instead of all at once.'
    )

    display_survey_directly = BooleanField(
        default=False,
        verbose_name='Display Question Directly',
        help_text='This is similar to polls, in which the questions are '
                  'displayed directly on the page, instead of displaying '
                  'a link to another page to complete the survey.'

    )
    your_words_competition = BooleanField(
        default=False,
        verbose_name='Is YourWords Competition',
        help_text='This will display the correct template for yourwords'
    )
    extra_style_hints = models.TextField(
        default='',
        null=True, blank=True,
        help_text=_(
            "Styling options that can be applied to this page "
            "and all its descendants"))
    content_panels = surveys_models.AbstractSurvey.content_panels + [
        FieldPanel('intro', classname='full'),
        ImageChooserPanel('image'),
        StreamFieldPanel('content'),
        InlinePanel('survey_form_fields', label='Form fields'),
        FieldPanel('thank_you_text', classname='full'),
        FieldPanel('submit_text', classname='full'),
        FieldPanel('homepage_button_text', classname='full'),
        InlinePanel('terms_and_conditions', label="Terms and Conditions"),
    ]

    settings_panels = surveys_models.AbstractSurvey.settings_panels + [
        MultiFieldPanel([
            FieldPanel('allow_anonymous_submissions'),
            FieldPanel('allow_multiple_submissions_per_user'),
            FieldPanel('show_results'),
            FieldPanel('show_results_as_percentage'),
            FieldPanel('multi_step'),
            FieldPanel('display_survey_directly'),
            FieldPanel('your_words_competition'),
        ], heading='Survey Settings'),
        MultiFieldPanel(
            [FieldRowPanel(
                [FieldPanel('extra_style_hints')], classname="label-above")],
            "Meta")
    ]

    def get_effective_extra_style_hints(self):
        return self.extra_style_hints

    def get_effective_image(self):
        return self.image

    def get_data_fields(self):
        data_fields = [
            ('username', _('Username')),
            ('created_at', _('Submission Date')),
        ]
        data_fields += [
            (field.clean_name, field.admin_label)
            for field in self.get_form_fields()
        ]
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

    def get_form(self, *args, **kwargs):
        prevent_required = kwargs.pop('prevent_required', False)
        form = super(MoloSurveyPage, self).get_form(*args, **kwargs)
        if prevent_required:
            for field in form.fields.values():
                field.required = False
        return form

    def get_form_class_for_step(self, step):
        return self.form_builder(step.object_list).get_form_class()

    def serve_questions(self, request):
        """
        Implements a simple multi-step form.

        Stores each step in the session.
        When the last step is submitted correctly, the whole form is saved in
        the DB.
        """
        session_key_data = 'survey_data-%s' % self.pk
        survey_data = json.loads(request.session.get(session_key_data, '{}'))

        paginator = SkipLogicPaginator(
            self.get_form_fields(),
            request.POST,
            survey_data,
        )

        is_last_step = False
        step_number = request.GET.get('p', 1)

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
            prev_form = prev_form_class(paginator.new_answers, page=self,
                                        user=request.user)
            if prev_form.is_valid():
                # If data for step is valid, update the session
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
                    data = json.loads(request.session[session_key_data])
                    form = self.get_form(
                        data,
                        page=self,
                        user=request.user,
                        prevent_required=True
                    )

                    if form.is_valid():
                        # Perform validation again for whole form.
                        # After successful validation, save data into DB,
                        # and remove from the session.
                        self.set_survey_as_submitted_for_session(request)

                        # We fill in the missing fields which were skipped with
                        # a default value
                        for question in self.get_form_fields():
                            if question.clean_name not in data:
                                form.cleaned_data[question.clean_name] = SKIP

                        self.process_form_submission(form)
                        del request.session[session_key_data]

                        return prev_step.success(self.slug)

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

    @cached_property
    def has_skip_logic(self):
        return any(field.has_skipping for field in self.get_form_fields())

    def serve(self, request, *args, **kwargs):
        if not self.allow_multiple_submissions_per_user \
                and self.has_user_submitted_survey(request, self.id):
            return render(request, self.template, self.get_context(request))

        if self.has_skip_logic or self.multi_step:
            return self.serve_questions(request)

        if request.method == 'POST':
            form = self.get_form(request.POST, page=self, user=request.user)

            if form.is_valid():
                self.set_survey_as_submitted_for_session(request)
                self.process_form_submission(form)

                # render the landing_page
                return redirect(
                    reverse('molo.surveys:success', args=(self.slug, )))

        return super(MoloSurveyPage, self).serve(request, *args, **kwargs)


class SurveyTermsConditions(Orderable):
    page = ParentalKey(MoloSurveyPage, related_name='terms_and_conditions')
    terms_and_conditions = models.ForeignKey(
        'wagtailcore.Page',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text=_('Terms and Conditions')
    )
    panels = [PageChooserPanel(
        'terms_and_conditions', 'core.FooterPage')]


class AdminLabelMixin(models.Model):
    admin_label = models.CharField(
        max_length=256,
        help_text=_('Column header used during CSV export of survey responses.'),
        default='',
    )

    class Meta:
        abstract = True


surveys_models.AbstractFormField._meta.get_field('label').verbose_name = 'Question'


surveys_models.AbstractFormField.panels.append(FieldPanel('admin_label'))


class SkipLogicMixin(models.Model):
    skip_logic = SkipLogicField()

    class Meta:
        abstract = True

    @property
    def has_skipping(self):
        return any(
            logic.value['skip_logic'] != SkipState.NEXT
            for logic in self.skip_logic
        )

    def choice_index(self, choice):
        if self.field_type == 'checkbox':
            # clean checkboxes have True/False
            try:
                return ['on', 'off'].index(choice)
            except ValueError:
                return [True, False].index(choice)
        return self.choices.split(',').index(choice)

    def next_action(self, choice):
        return self.skip_logic[self.choice_index(choice)].value['skip_logic']

    def is_next_action(self, choice, *actions):
        if self.has_skipping:
            return self.next_action(choice) in actions
        return False

    def next_page(self, choice):
        logic = self.skip_logic[self.choice_index(choice)]
        return logic.value[self.next_action(choice)]

    def clean(self):
        super(SkipLogicMixin, self).clean()
        if not self.required and self.skip_logic:

            raise ValidationError(
                {'required': _('Questions with skip logic must be required.')}
            )

    def save(self, *args, **kwargs):
        self.choices = ','.join(
            choice.value['choice'].replace(',', u'\u201A')
            for choice in self.skip_logic
        )
        return super(SkipLogicMixin, self).save(*args, **kwargs)


class MoloSurveyFormField(SkipLogicMixin, AdminLabelMixin, AbstractFormField):
    page = ParentalKey(MoloSurveyPage, related_name='survey_form_fields')

    class Meta(AbstractFormField.Meta):
        pass


surveys_models.AbstractFormField.panels[4] = SkipLogicStreamPanel('skip_logic')


class MoloSurveySubmission(surveys_models.AbstractFormSubmission):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True
    )
    article_page = models.ForeignKey(
        'core.ArticlePage',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text='Page to which the entry was converted to'
    )

    def get_data(self):
        form_data = super(MoloSurveySubmission, self).get_data()
        form_data.update({
            'username': self.user.username if self.user else 'Anonymous',
        })
        return form_data


# Personalised Surveys
def get_personalisable_survey_content_panels():
    """
    Replace panel for "survey_form_fields" with
    panel pointing to the custom form field model.
    """
    panels = [
        FieldPanel('segment')
    ]

    for panel in MoloSurveyPage.content_panels:
        if isinstance(panel, InlinePanel) and \
                panel.relation_name == 'survey_form_fields':
            panel = InlinePanel('personalisable_survey_form_fields',
                                label=_('personalisable form fields'))
        panels.append(panel)

    return panels


class PersonalisableSurvey(MoloSurveyPage):
    """
    Survey page that enables form fields to be segmented with
    wagtail-personalisation.
    """
    segment = models.ForeignKey('wagtail_personalisation.Segment',
                                on_delete=models.SET_NULL, blank=True,
                                null=True,
                                help_text=_(
                                    'Leave it empty to show this survey'
                                    'to every user.'))
    content_panels = get_personalisable_survey_content_panels()
    template = MoloSurveyPage.template

    base_form_class = PersonalisableMoloSurveyForm

    class Meta:
        verbose_name = _('personalisable survey')

    def is_front_end_request(self):
        return (hasattr(self, 'request') and
                not getattr(self.request, 'is_preview', False))

    def get_form_fields(self):
        """Get form fields for particular segments."""
        # Get only segmented form fields if serve() has been called
        # (because the page is being seen by user on the front-end)
        if self.is_front_end_request():
            user_segments_ids = [
                s.id for s in get_segment_adapter(self.request).get_segments()
            ]

            return self.personalisable_survey_form_fields.filter(
                Q(segment=None) | Q(segment_id__in=user_segments_ids)
            )

        # Return all form fields if there's no request passed
        # (used on the admin site so serve() will not be called).
        return self.personalisable_survey_form_fields.select_related('segment')

    def get_data_fields(self):
        """
        Get survey's form field's labels with segment names
        if there's one associated.
        """
        data_fields = [
            ('created_at', _('Submission Date')),
        ]

        # Add segment name to a field label if it is segmented.
        for field in self.get_form_fields():
            label = field.label

            if field.segment:
                label = '%s (%s)' % (label, field.segment.name)

            data_fields.append((field.clean_name, label))

        return data_fields

    def serve(self, request, *args, **kwargs):
        # We need request data in self.get_form_fields() to perform
        # segmentation.
        # TODO(tmkn): This is quite hacky, need to come up with better solution
        self.request = request

        # Check whether it is segmented and raise 404 if segments do not match
        if not getattr(request, 'is_preview', False):
            if (self.segment_id and
                get_segment_adapter(request).get_segment_by_id(
                    self.segment_id) is None):
                raise Http404("Survey does not match your segments.")

        return super(PersonalisableSurvey, self).serve(
            request, *args, **kwargs)


class PersonalisableSurveyFormField(SkipLogicMixin, AdminLabelMixin, AbstractFormField):
    """
    Form field that has a segment assigned.
    """
    page = ParentalKey(PersonalisableSurvey, on_delete=models.CASCADE,
                       related_name='personalisable_survey_form_fields')
    segment = models.ForeignKey(
        'wagtail_personalisation.Segment',
        on_delete=models.PROTECT, blank=True, null=True,
        help_text=_('Leave it empty to show this field to every user.'))

    panels = [
        FieldPanel('segment')
    ] + AbstractFormField.panels

    def __str__(self):
        return '%s - %s' % (self.page, self.label)

    class Meta(AbstractFormField.Meta):
        verbose_name = _('personalisable form field')


class SegmentUserGroup(models.Model):
    name = models.CharField(max_length=254)
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='segment_groups',
    )

    def __str__(self):
        return self.name
