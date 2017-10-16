from django import forms
from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import six
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from wagtail.wagtailadmin.edit_handlers import FieldPanel, FieldRowPanel, PageChooserPanel

from wagtail_personalisation.adapters import get_segment_adapter
from wagtail_personalisation.rules import AbstractBaseRule

from .edit_handlers import FieldQueryPanel


class SurveySubmissionDataRule(AbstractBaseRule):
    EQUALS = 'eq'
    CONTAINS = 'in'

    OPERATOR_CHOICES = (
        (EQUALS, _('equals')),
        (CONTAINS, _('contains')),
    )

    survey = models.ForeignKey('PersonalisableSurvey',
                               verbose_name=_('survey'),
                               on_delete=models.CASCADE)
    field_name = models.CharField(
        _('field name'), max_length=255,
        help_text=_('Field\'s label in a lower-case '
                    'format with spaces replaced by '
                    'dashes. For possible choices '
                    'please input any text and save, '
                    'so it will be displayed in the '
                    'error messages below the '
                    'field.'))
    expected_response = models.CharField(
        _('expected response'), max_length=255,
        help_text=_('When comparing text values, please input text. Comparison'
                    ' on text is always case-insensitive. Multiple choice '
                    'values must be separated with commas.'))
    operator = models.CharField(
        _('operator'), max_length=3,
        choices=OPERATOR_CHOICES, default=CONTAINS,
        help_text=_('When using the "contains" operator'
                    ', "expected response" can '
                    'contain a small part of user\'s '
                    'response and it will be matched. '
                    '"Exact" would match responses '
                    'that are exactly the same as the '
                    '"expected response".'))

    panels = [
        PageChooserPanel('survey'),
        FieldPanel('field_name'),
        FieldPanel('operator'),
        FieldPanel('expected_response')
    ]

    class Meta:
        verbose_name = _('Survey submission rule')

    @cached_property
    def field_model(self):
        return apps.get_model('personalise', 'PersonalisableSurveyFormField')

    @property
    def survey_submission_model(self):
        from molo.surveys.models import MoloSurveySubmission

        return MoloSurveySubmission

    def get_expected_field(self):
        try:
            return self.survey.get_form().fields[self.field_name]
        except KeyError:
            raise self.field_model.DoesNotExist

    def get_expected_field_python_value(self, raise_exceptions=True):
        try:
            field = self.get_expected_field()
            self.expected_response = self.expected_response.strip()
            python_value = self.expected_response

            if isinstance(field, forms.MultipleChoiceField):
                # Eliminate duplicates, strip whitespaces,
                # eliminate empty values
                python_value = [v for v in {v.strip() for v in
                                            self.expected_response.split(',')}
                                if v]
                self.expected_response = ','.join(python_value)

                return python_value

            if isinstance(field, forms.BooleanField):
                if self.expected_response not in '01':
                    raise ValidationError({
                        'expected_response': [
                            _('Please use "0" or "1" on this field.')
                        ]
                    })
                return self.expected_response == '1'

            return python_value

        except (ValidationError, self.field_model.DoesNotExist):
            if raise_exceptions:
                raise

    def get_survey_submission_of_user(self, user):
        return self.survey_submission_model.objects.get(
            user=user, page_id=self.survey_id)

    def clean(self):
        # Do not call clean() if we have no survey set.
        if not self.survey_id:
            return

        # Make sure field name is a valid name
        field_names = [f.clean_name for f in self.survey.get_form_fields()]

        if self.field_name not in field_names:
            raise ValidationError({
                'field_name': [_('You need to choose valid field name out '
                                 'of: "%s".') % '", "'.join(field_names)]
            })

        # Convert value from the rule into Python value.
        python_value = self.get_expected_field_python_value()

        # Get this particular's field instance from the survey's form
        # so we can do validation on the value.
        try:
            self.get_expected_field().clean(python_value)
        except ValidationError as error:
            raise ValidationError({
                'expected_response': error
            })

    def test_user(self, request):
        # Must be logged-in to use this rule
        if not request.user.is_authenticated():
            return False

        try:
            survey_submission = self.get_survey_submission_of_user(
                request.user)
        except self.survey_submission_model.DoesNotExist:
            # No survey found so return false
            return False
        except self.survey_submission_model.MultipleObjectsReturned:
            # There should not be two survey submissions, but just in case
            # let's return false since we don't want to be guessing what user
            # meant in their response.
            return False

        # Get dict with user's survey submission to a particular question
        user_response = survey_submission.get_data().get(self.field_name)

        if not user_response:
            return False

        python_value = self.get_expected_field_python_value()

        # Compare user's response
        try:
            # Convert lists to sets for easy comparison
            if isinstance(python_value, list) \
                    and isinstance(user_response, list):
                if self.operator == self.CONTAINS:
                    return set(python_value).issubset(user_response)

                if self.operator == self.EQUALS:
                    return set(python_value) == set(user_response)

            if isinstance(python_value, six.string_types) \
                    and isinstance(user_response, six.string_types):
                if self.operator == self.CONTAINS:
                    return python_value.lower() in user_response.lower()

                return python_value.lower() == user_response.lower()

            return python_value == user_response
        except ValidationError:
            # In case survey has been modified and we cannot obtain Python
            # value, we want to return false.
            return False
        except self.field_model.DoesNotExist:
            # In case field does not longer exist on the survey
            # return false. We cannot compare its value if
            # we do not know its type (hence it needs to be on the survey).
            return False

    def description(self):
        try:
            field_name = self.get_expected_field().label
        except self.field_model.DoesNotExist:
            field_name = self.field_name

        return {
            'title': _('Based on survey submission of users'),
            'value': _('%s - %s  "%s"') % (
                self.survey,
                field_name,
                self.expected_response
            )
        }


class GroupMembershipRule(AbstractBaseRule):
    """wagtail-personalisation rule based on user's group membership."""
    group = models.ForeignKey('auth.Group', on_delete=models.PROTECT,
                              help_text=_('User must be part of this group to '
                                          'activate the rule.'))

    panels = [
        FieldPanel('group')
    ]

    class Meta:
        verbose_name = _('Group membership rule')

    def description(self):
        return {
            'title': _('Based on survey group memberships of users'),
            'value': _('Member of: "%s"') % self.group
        }

    def test_user(self, request):
        # Ignore not-logged in users
        if not request.user.is_authenticated():
            return False

        # Check whether user is part of a group
        return request.user.groups.filter(id=self.group_id).exists()


class ArticleTagRule(AbstractBaseRule):
    EQUALS = 'eq'
    GREATER_THAN = 'gt'
    LESS_THAN = 'lt'

    OPERATORS = {
        EQUALS: lambda a, b: a == b,
        GREATER_THAN: lambda a, b: a > b,
        LESS_THAN: lambda a, b: a < b,
    }

    OPERATOR_CHOICES = (
        (EQUALS, _('equals')),
        (GREATER_THAN, _('greater than')),
        (LESS_THAN, _('less than')),
    )

    tag = models.ForeignKey('taggit.Tag',
                            on_delete=models.CASCADE)

    operator = models.CharField(
        _('operator'),
        max_length=3,
        choices=OPERATOR_CHOICES,
        default=EQUALS,
    )
    count = models.IntegerField()

    # Naive datetimes as we are not storing the datetime based on the users
    # timezone.
    date_from = models.DateTimeField(blank=True, null=True)
    date_to = models.DateTimeField(
        blank=True,
        null=True,
        help_text=_(
            'All times are UTC. Leave both fields blank to search for all time.'
        ),
    )

    panels = [
        FieldQueryPanel('tag', ~Q(core_articlepagetag_items__isnull=True)),
        FieldRowPanel(
            [
                FieldPanel('operator'),
                FieldPanel('count'),
            ]
        ),
        FieldPanel('date_from'),
        FieldPanel('date_to'),
    ]

    class Meta:
        verbose_name = _('Article tag rule')

    def clean(self):
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise ValidationError(
                    {
                        'date_from': [_('Date from must be before date to.')],
                        'date_to': [_('Date from must be before date to.')],
                    }
                )

        if self.count > self.tag.core_articlepagetag_items.count():
                raise ValidationError(
                    {
                        'count': [_('Count can not exceed the number of articles.')],
                    }
                )


    def test_user(self, request):
        operator = self.OPERATORS[self.operator]
        adapter = get_segment_adapter(request)
        visit_count = adapter.get_tag_count(
            self.tag,
            self.date_from,
            self.date_to,
        )

        return operator(visit_count, self.count)

    def description(self):
        return {
            'title': _('These users visited {}').format(
                self.tag
            ),
            'value': _('{} {} times').format(
                self.get_operator_display(),
                self.count
            ),
        }
