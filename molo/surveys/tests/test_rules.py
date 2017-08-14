import pytest

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group
from django.test import TestCase, RequestFactory

from molo.core.tests.base import MoloTestCaseMixin
from molo.surveys.models import SurveysIndexPage


from ..models import PersonalisableSurveyFormField, PersonalisableSurvey
from ..rules import SurveySubmissionDataRule, GroupMembershipRule


@pytest.mark.django_db
class TestSurveyDataRuleSegmentation(TestCase, MoloTestCaseMixin):
    def setUp(self):
        # Fabricate a request with a logged-in user
        # so we can use it to test the segment rule
        self.mk_main()
        self.request_factory = RequestFactory()
        self.request = self.request_factory.get('/')
        self.request.user = get_user_model().objects.create_user(
            username='tester', email='tester@example.com', password='tester')

        # Create survey
        self.survey = PersonalisableSurvey(title='Test Survey')
        SurveysIndexPage.objects.first().add_child(instance=self.survey)

        # Create survey form fields
        self.singleline_text = PersonalisableSurveyFormField.objects.create(
            field_type='singleline', label='Singleline Text', page=self.survey)
        self.checkboxes = PersonalisableSurveyFormField.objects.create(
            field_type='checkboxes', label='Checboxes Field', page=self.survey,
            choices='choice 1, choice 2, choice 3')
        self.checkbox = PersonalisableSurveyFormField.objects.create(
            field_type='checkbox', label='Checbox Field', page=self.survey)
        self.number = PersonalisableSurveyFormField.objects.create(
            field_type='number', label='Number Field', page=self.survey)

        # Create survey submission
        data = {
            self.singleline_text.clean_name: 'super random text',
            self.checkboxes.clean_name: ['choice 3', 'choice 1'],
            self.checkbox.clean_name: True,
            self.number.clean_name: 5
        }
        form = self.survey.get_form(
            data, page=self.survey, user=self.request.user)

        assert form.is_valid(), \
            'Could not validate submission form. %s' % repr(form.errors)

        self.survey.process_form_submission(form)

        self.survey.refresh_from_db()

    def test_passing_string_rule_with_equal_operator(self):
        rule = SurveySubmissionDataRule(
            survey=self.survey, operator=SurveySubmissionDataRule.EQUALS,
            expected_response='super random text',
            field_name=self.singleline_text.clean_name)

        self.assertTrue(rule.test_user(self.request))

    def test_failing_string_rule_with_equal_operator(self):
        rule = SurveySubmissionDataRule(
            survey=self.survey, operator=SurveySubmissionDataRule.EQUALS,
            expected_response='super random textt',
            field_name=self.singleline_text.clean_name)

        self.assertFalse(rule.test_user(self.request))

    def test_passing_string_rule_with_contain_operator(self):
        rule = SurveySubmissionDataRule(
            survey=self.survey, operator=SurveySubmissionDataRule.CONTAINS,
            expected_response='text',
            field_name=self.singleline_text.clean_name)

        self.assertTrue(rule.test_user(self.request))

    def test_failing_string_rule_with_contain_operator(self):
        rule = SurveySubmissionDataRule(
            survey=self.survey, operator=SurveySubmissionDataRule.CONTAINS,
            expected_response='word',
            field_name=self.singleline_text.clean_name)

        self.assertFalse(rule.test_user(self.request))

    def test_padding_checkboxes_rule_with_equal_operator(self):
        rule = SurveySubmissionDataRule(
            survey=self.survey, operator=SurveySubmissionDataRule.CONTAINS,
            expected_response=' choice 3 , choice 1 ',
            field_name=self.checkboxes.clean_name)

        self.assertTrue(rule.test_user(self.request))

    def test_failing_checkboxes_rule_with_equal_operator(self):
        rule = SurveySubmissionDataRule(
            survey=self.survey, operator=SurveySubmissionDataRule.CONTAINS,
            expected_response='choice2,choice1',
            field_name=self.checkboxes.clean_name)

        self.assertFalse(rule.test_user(self.request))

    def test_passing_checkboxes_rule_with_contain_operator(self):
        rule = SurveySubmissionDataRule(
            survey=self.survey, operator=SurveySubmissionDataRule.CONTAINS,
            expected_response='choice 3',
            field_name=self.checkboxes.clean_name)

        self.assertTrue(rule.test_user(self.request))

    def test_failing_checkboxes_rule_with_contain_operator(self):
        rule = SurveySubmissionDataRule(
            survey=self.survey, operator=SurveySubmissionDataRule.CONTAINS,
            expected_response='choice 2, choice 3',
            field_name=self.checkboxes.clean_name)

        self.assertFalse(rule.test_user(self.request))

    def test_passing_checkbox_rule(self):
        rule = SurveySubmissionDataRule(
            survey=self.survey, operator=SurveySubmissionDataRule.CONTAINS,
            expected_response='1',
            field_name=self.checkbox.clean_name)

        self.assertTrue(rule.test_user(self.request))

    def test_failing_checkbox_rule(self):
        rule = SurveySubmissionDataRule(
            survey=self.survey, operator=SurveySubmissionDataRule.CONTAINS,
            expected_response='0',
            field_name=self.checkbox.clean_name)

        self.assertFalse(rule.test_user(self.request))

    def test_passing_number_rule(self):
        rule = SurveySubmissionDataRule(
            survey=self.survey, operator=SurveySubmissionDataRule.CONTAINS,
            expected_response='5',
            field_name=self.number.clean_name)

        self.assertTrue(rule.test_user(self.request))

    def test_failing_number_rule(self):
        rule = SurveySubmissionDataRule(
            survey=self.survey, operator=SurveySubmissionDataRule.CONTAINS,
            expected_response='4',
            field_name=self.number.clean_name)

        self.assertFalse(rule.test_user(self.request))

    def test_not_logged_in_user_fails(self):
        rule = SurveySubmissionDataRule(
            survey=self.survey, operator=SurveySubmissionDataRule.CONTAINS,
            expected_response='er ra',
            field_name=self.singleline_text.clean_name)

        # Passes for logged-in user
        self.assertTrue(rule.test_user(self.request))

        # Fails for logged-out user
        self.request.user = AnonymousUser()
        self.assertFalse(rule.test_user(self.request))


class TestGroupMembershipRuleSegmentation(TestCase, MoloTestCaseMixin):
    def setUp(self):
        # Fabricate a request with a logged-in user
        # so we can use it to test the segment rule
        self.mk_main()
        self.request_factory = RequestFactory()
        self.request = self.request_factory.get('/')
        self.request.user = get_user_model().objects.create_user(
            username='tester', email='tester@example.com', password='tester')

        self.group = Group.objects.create(name='Super Test Group!')

        self.request.user.groups.add(self.group)

    def test_user_membership_rule_when_they_are_member(self):
        rule = GroupMembershipRule(group=self.group)

        self.assertTrue(rule.test_user(self.request))

    def test_user_membership_rule_when_they_are_not_member(self):
        group = Group.objects.create(name='Wagtail-like creatures')
        rule = GroupMembershipRule(group=group)

        self.assertFalse(rule.test_user(self.request))

    def test_user_membership_rule_on_not_logged_in_user(self):
        self.request.user = AnonymousUser()
        rule = GroupMembershipRule(group=self.group)

        self.assertFalse(rule.test_user(self.request))
