from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test.client import Client
from molo.core.tests.base import MoloTestCaseMixin
from molo.surveys.models import MoloSurveyPage, MoloSurveyFormField

User = get_user_model()


class TestSurveyViews(TestCase, MoloTestCaseMixin):
    def setUp(self):
        self.client = Client()

        self.mk_main()

        self.section = self.mk_section(self.english)
        self.article = self.mk_article(self.section)

        self.user = User.objects.create_user(
            username='tester',
            email='tester@example.com',
            password='tester')

    def create_molo_survey_page(self, parent, **kwargs):
        molo_survey_page = MoloSurveyPage(
            title='Test Survey', slug='test-survey',
            intro='Introduction to Test Survey ...',
            thank_you_text='Thank you for taking the Test Survey',
            **kwargs
        )

        parent.add_child(instance=molo_survey_page)

        molo_survey_form_field = MoloSurveyFormField.objects.create(
            page=molo_survey_page,
            sort_order=1,
            label='Your favourite animal',
            field_type='singleline',
            required=True
        )

        return molo_survey_page, molo_survey_form_field

    def test_anonymous_submissions_not_allowed_by_default(self):
        molo_survey_page, molo_survey_form_field = \
            self.create_molo_survey_page(parent=self.english)

        response = self.client.get(molo_survey_page.url)

        self.assertContains(response, molo_survey_page.title)
        self.assertContains(response, 'Please log in to take this survey.')

    def test_submit_survey_as_logged_in_user(self):
        molo_survey_page, molo_survey_form_field = \
            self.create_molo_survey_page(parent=self.english)

        self.client.login(username='tester', password='tester')

        response = self.client.get(molo_survey_page.url)

        self.assertContains(response, molo_survey_page.title)
        self.assertContains(response, molo_survey_page.intro)
        self.assertContains(response, molo_survey_form_field.label)

        response = self.client.post(molo_survey_page.url, {
            molo_survey_form_field.label.lower().replace(' ', '-'): 'python'
        })

        self.assertContains(response, molo_survey_page.thank_you_text)

        # for test_multiple_submissions_not_allowed_by_default
        return molo_survey_page.url

    def test_anonymous_submissions_option(self):
        molo_survey_page, molo_survey_form_field = \
            self.create_molo_survey_page(parent=self.english,
                                         allow_anonymous_submissions=True)

        response = self.client.get(molo_survey_page.url)

        self.assertContains(response, molo_survey_page.title)
        self.assertContains(response, molo_survey_page.intro)
        self.assertContains(response, molo_survey_form_field.label)

        response = self.client.post(molo_survey_page.url, {
            molo_survey_form_field.label.lower().replace(' ', '-'): 'python'
        })

        self.assertContains(response, molo_survey_page.thank_you_text)

        # for test_multiple_submissions_not_allowed_by_default_anonymous
        return molo_survey_page.url

    def test_multiple_submissions_not_allowed_by_default(self):
        molo_survey_page_url = self.test_submit_survey_as_logged_in_user()

        response = self.client.get(molo_survey_page_url)

        self.assertContains(response,
                            'You have already completed this survey.')

    def test_multiple_submissions_not_allowed_by_default_anonymous(self):
        molo_survey_page_url = self.test_anonymous_submissions_option()

        response = self.client.get(molo_survey_page_url)

        self.assertContains(response,
                            'You have already completed this survey.')

    def test_multiple_submissions_option(self, anonymous=False):
        molo_survey_page, molo_survey_form_field = \
            self.create_molo_survey_page(
                parent=self.english,
                allow_multiple_submissions_per_user=True
            )

        if not anonymous:
            self.client.login(username='tester', password='tester')

        for _ in range(2):
            response = self.client.get(molo_survey_page.url)

            self.assertContains(response, molo_survey_page.title)
            self.assertContains(response, molo_survey_page.intro)
            self.assertContains(response, molo_survey_form_field.label)

            response = self.client.post(molo_survey_page.url, {
                molo_survey_form_field.label.lower().replace(' ', '-'):
                    'python'
            })

            self.assertContains(response, molo_survey_page.thank_you_text)

    def test_multiple_submissions_option_anonymous(self):
        self.test_multiple_submissions_option(True)
