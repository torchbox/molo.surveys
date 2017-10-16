import csv
from collections import defaultdict

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.forms.utils import ErrorList
from django.utils.translation import ugettext_lazy as _

from wagtail.wagtailadmin.forms import WagtailAdminPageForm

from .blocks import SkipState, VALID_SKIP_SELECTORS


class CSVGroupCreationForm(forms.ModelForm):
    """Create group with initial users supplied via CSV file."""
    csv_file = forms.FileField(
        label=_('CSV file'),
        help_text=_('Please attach a CSV file with the first column containing'
                    ' usernames of users that you want to be added to '
                    'this group.'))

    class Meta:
        model = Group
        fields = ("name",)

    def clean_csv_file(self):
        """Read CSV file and save the users to self.initial_users."""
        csv_file = self.cleaned_data['csv_file']

        # Sniff CSV file
        try:
            dialect = csv.Sniffer().sniff(csv_file.read(1024))
        except csv.Error:
            raise forms.ValidationError(_('Uploaded file does not appear to be'
                                          ' in CSV format.'))

        csv_file.seek(0)

        # Instantiate CSV Reader
        csv_file_reader = csv.reader(csv_file, dialect)

        # Check whether file has a header
        try:
            if csv.Sniffer().has_header(csv_file.read(1024)):
                next(csv_file_reader)  # Skip the header
        except csv.Error:
            raise forms.ValidationError(_('Uploaded file does not appear to be'
                                          ' in CSV format.'))

        # Gather all usernames from the CSV file.
        usernames = set()
        for row in csv_file_reader:
            try:
                username = row[0]
            except IndexError:
                # Skip empty row
                continue
            else:
                # Skip empty username field
                if username:
                    usernames.add(username)

        if not usernames:
            raise forms.ValidationError(_('Your CSV file does not appear to '
                                          'contain any usernames.'))

        queryset = get_user_model().objects.filter(username__in=usernames)
        difference = usernames - set(queryset.values_list('username',
                                                          flat=True))
        if difference:
            raise forms.ValidationError(_('Please make sure your file contains'
                                          ' valid data. '
                                          'Those usernames do not exist: '
                                          '"%s".') % '", "'.join(difference))

        # Store users temporarily as a property so we can
        # add them when user calls save() on the form.
        self.__initial_users = queryset

    def save(self, *args, **kwargs):
        """Save the group instance and add initial users to it."""
        # Save the group instance
        group = super(CSVGroupCreationForm, self).save(*args, **kwargs)

        # Add users to the group
        group.user_set.add(*self.__initial_users)


class BaseMoloSurveyForm(WagtailAdminPageForm):
    def clean(self):
        cleaned_data = super(BaseMoloSurveyForm, self).clean()
        for form in self.formsets[self.form_field_name]:
            self._clean_errors = defaultdict(lambda: defaultdict(list))
            if form.is_valid():
                data = form.cleaned_data
                for i, logic in enumerate(data['skip_logic']):
                    if logic.value['skip_logic'] == SkipState.SURVEY:
                        survey = logic.value['survey']
                        self.clean_survey(i, survey)
                    if logic.value['skip_logic'] == SkipState.QUESTION:
                        sort_order = logic.value['question'] - 1
                        questions = (
                            getattr(self.instance, self.form_field_name)
                        )
                        question = questions.get(sort_order=sort_order)
                        self.clean_question(i, data['segment'], question)
                if self.clean_errors:
                    form._errors = self.clean_errors

        return cleaned_data

    def save(self, commit):
        # Tidy up the skip logic when field cant have skip logic
        for form in self.formsets[self.form_field_name]:
            field_type = form.instance.field_type
            if field_type not in VALID_SKIP_SELECTORS:
                if field_type != 'checkboxes':
                    form.instance.skip_logic = []
                else:
                    for skip_logic in form.instance.skip_logic:
                        skip_logic.value['skip_logic'] = SkipState.NEXT
                        skip_logic.value['question'] = None
                        skip_logic.value['survey'] = None

        return super(BaseMoloSurveyForm, self).save(commit)


    def clean_question(self, position, *args):
        self.clean_formset_field('question', position, *args)

    def clean_survey(self, position, *args):
        self.clean_formset_field('survey', position, *args)

    def clean_formset_field(self, field, position, *args):
        for method in getattr(self, field + '_clean_methods', []):
            error = getattr(self, method)(*args)
            if error:
                self.add_stream_field_error(position, field, error)

    def check_doesnt_loop_to_self(self, survey):
        if survey and self.instance == survey:
            return _('Cannot skip to self, please select a different survey.')

    def add_stream_field_error(self, position, field, message):
        self._clean_errors[position][field].append(message)

    @property
    def clean_errors(self):
        if self._clean_errors.keys():
            params = {
                key: ErrorList(
                    [ValidationError('Error in form', params=value)]
                )
                for key, value in self._clean_errors.items()
            }
            return {
                'skip_logic': ErrorList([ValidationError(
                    'Skip Logic Error',
                    params=params,
                )])
            }


class MoloSurveyForm(BaseMoloSurveyForm):
    form_field_name = 'survey_form_fields'
    survey_clean_methods = [
        'check_doesnt_loop_to_self',
        'check_doesnt_link_personalised_survey',
    ]

    def check_doesnt_link_to_peronsalised_survey(self, survey):
        try:
            segment = survey.personalisablesurvey.segment
        except AttributeError:
            pass
        else:
            # Can only link a survey without a segments
            if segment:
                return _('Cannot select a survey with a segment.')


class PersonalisableMoloSurveyForm(BaseMoloSurveyForm):
    form_field_name = 'personalisable_survey_form_fields'
    survey_clean_methods = [
        'check_doesnt_loop_to_self',
        'check_survey_link_valid',
    ]

    question_clean_methods = [
        'check_question_segment_ok',
    ]

    def check_question_segment_ok(self, current_segment, linked_question):
        segment = linked_question.segment
        # Cannot link from None to segment, but can link from segment to None
        if (segment and not current_segment) or (segment != current_segment):
            return _('Cannot link to a question with a different segment.')

    def check_survey_link_valid(self, survey):
        try:
            segment = survey.personalisablesurvey.segment
        except AttributeError:
            pass
        else:
            # Can only link a survey without segments or the same segment
            if segment and segment != self.instance.segment:
                return _('Cannot select a survey with a different segment.')
