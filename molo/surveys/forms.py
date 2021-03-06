import csv
from collections import defaultdict, OrderedDict

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.forms.utils import ErrorList, flatatt
from django.utils.encoding import force_text
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _
from django.utils import six

from wagtail.wagtailadmin.forms import WagtailAdminPageForm
from wagtailsurveys.forms import FormBuilder

from .blocks import SkipState, VALID_SKIP_LOGIC, VALID_SKIP_SELECTORS


class CharacterCountWidget(forms.TextInput):
    class Media:
        js = ('js/widgets/character_count.js',)

    def render(self, name, value, attrs=None):
        if value is None:
            value = ''
        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        max_length = final_attrs['maxlength']
        maximum_text = _('Maximum: {max_length}').format(max_length=max_length)
        if value != '':
            # Only add the 'value' attribute if a value is non-empty.
            final_attrs['value'] = force_text(self._format_value(value))
        return format_html('<input {} /><span>{}</span>',
                           flatatt(final_attrs),
                           maximum_text)


class MultiLineWidget(forms.Textarea):
    def render(self, name, value, attrs=None):
        if value is None:
            value = ''
        final_attrs = self.build_attrs(attrs, name=name)
        return format_html('<textarea{}>\r\n{}</textarea><span>{}</span>',
                           flatatt(final_attrs),
                           force_text(value),
                           _('No limit'))


class SurveysFormBuilder(FormBuilder):
    def create_singleline_field(self, field, options):
        options['widget'] = CharacterCountWidget
        return super(SurveysFormBuilder, self).create_singleline_field(field,
                                                                       options)

    def create_multiline_field(self, field, options):
        options['widget'] = MultiLineWidget
        return forms.CharField(**options)

    @property
    def formfields(self):
        formfields = OrderedDict()

        for field in self.fields:
            options = self.get_field_options(field)

            if field.field_type in self.FIELD_TYPES:
                method = getattr(self,
                                 self.FIELD_TYPES[field.field_type].__name__)
                formfields[field.clean_name] = method(field, options)
            else:
                raise Exception("Unrecognised field type: " + field.field_type)

        return formfields


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

        question_data = {}
        for form in self.formsets[self.form_field_name]:
            form.is_valid()
            question_data[form.cleaned_data['ORDER']] = form

        for form in question_data.values():
            self._clean_errors = {}
            if form.is_valid():
                data = form.cleaned_data
                if data['field_type'] == 'checkbox':
                    if len(data['skip_logic']) != 2:
                        self.add_form_field_error(
                            'field_type',
                            _('Checkbox type questions must have 2 Answer '
                              'Options: a True and False'),
                        )
                elif data['field_type'] in VALID_SKIP_LOGIC:
                    for i, logic in enumerate(data['skip_logic']):
                        if not logic.value['choice']:
                            self.add_stream_field_error(
                                i,
                                'choice',
                                _('This field is required.'),
                            )

                for i, logic in enumerate(data['skip_logic']):
                    if logic.value['skip_logic'] == SkipState.SURVEY:
                        survey = logic.value['survey']
                        self.clean_survey(i, survey)
                    if logic.value['skip_logic'] == SkipState.QUESTION:
                        target = question_data.get(logic.value['question'])
                        target_data = target.cleaned_data
                        self.clean_question(i, data, target_data)
                if self.clean_errors:
                    form._errors = self.clean_errors

            elif self.form_cant_have_skip_errors(form):
                del form._errors['skip_logic']

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
            elif field_type == 'checkbox':
                for skip_logic in form.instance.skip_logic:
                    skip_logic.value['choice'] = ''

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

    def form_cant_have_skip_errors(self, form):
        return (
            form.has_error('skip_logic') and
            form.cleaned_data['field_type'] not in VALID_SKIP_LOGIC
        )

    def check_doesnt_loop_to_self(self, survey):
        if survey and self.instance == survey:
            return _('Cannot skip to self, please select a different survey.')

    def add_form_field_error(self, field, message):
        if field not in self._clean_errors:
            self._clean_errors[field] = list()
        self._clean_errors[field].append(message)

    def add_stream_field_error(self, position, field, message):
        if position not in self._clean_errors:
            self._clean_errors[position] = defaultdict(list)
        self._clean_errors[position][field].append(message)

    @property
    def clean_errors(self):
        if self._clean_errors.keys():
            params = {
                key: ErrorList(
                    [ValidationError('Error in form', params=value)]
                )
                for key, value in self._clean_errors.items()
                if isinstance(key, int)
            }
            errors = {
                key: ValidationError(value)
                for key, value in self._clean_errors.items()
                if isinstance(key, six.string_types)
            }
            errors.update({
                'skip_logic': ErrorList([ValidationError(
                    'Skip Logic Error',
                    params=params,
                )])
            })
            return errors


class MoloSurveyForm(BaseMoloSurveyForm):
    form_field_name = 'survey_form_fields'
    survey_clean_methods = [
        'check_doesnt_loop_to_self',
        'check_doesnt_link_to_personalised_survey',
    ]

    def check_doesnt_link_to_personalised_survey(self, survey):
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

    def check_question_segment_ok(self, question, target):
        # Cannot link from None to segment, but can link from segment to None
        current_segment = question.get('segment')
        linked_segment = target.get('segment')
        if linked_segment and (linked_segment != current_segment):
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
