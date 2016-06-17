from django.test import TestCase
from molo.core.tests.base import MoloTestCaseMixin
from molo.surveys.models import MoloSurveyPage, MoloSurveySubmission


class TestSurveyModels(TestCase, MoloTestCaseMixin):
    def test_submission_class(self):
        submission_class = MoloSurveyPage().get_submission_class()

        self.assertIs(submission_class, MoloSurveySubmission)

    def test_submission_class_get_data_includes_username(self):
        data = MoloSurveyPage().get_submission_class()(
            form_data='{}'
        ).get_data()
        self.assertIn('username', data)
