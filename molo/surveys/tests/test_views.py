from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client

from molo.core.models import SiteLanguage, Main
from molo.core.tests.base import MoloTestCaseMixin
from molo.surveys.models import (MoloSurveyPage, MoloSurveyFormField,
                                 SurveysIndexPage)

from bs4 import BeautifulSoup

User = get_user_model()


class TestSurveyViews(TestCase, MoloTestCaseMixin):
    def setUp(self):
        self.client = Client()
        self.english = SiteLanguage.objects.create(locale='en')
        self.french = SiteLanguage.objects.create(locale='fr')
        self.mk_main()

        self.section = self.mk_section(self.section_index, title='section')
        self.article = self.mk_article(self.section, title='article')

        # Create surveys index pages
        self.surveys_index = SurveysIndexPage(title='Surveys', slug='surveys')
        self.main.add_child(instance=self.surveys_index)

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
            self.create_molo_survey_page(parent=self.section_index)

        response = self.client.get(molo_survey_page.url)

        self.assertContains(response, molo_survey_page.title)
        self.assertContains(response, 'Please log in to take this survey')

    def test_submit_survey_as_logged_in_user(self):
        molo_survey_page, molo_survey_form_field = \
            self.create_molo_survey_page(parent=self.section_index)

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
            self.create_molo_survey_page(
                parent=self.section_index,
                allow_anonymous_submissions=True
            )

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
                parent=self.section_index,
                allow_multiple_submissions_per_user=True,
                allow_anonymous_submissions=anonymous
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

    def test_show_results_option(self):
        molo_survey_page, molo_survey_form_field = \
            self.create_molo_survey_page(
                parent=self.section_index,
                allow_anonymous_submissions=True,
                show_results=True
            )

        response = self.client.get(molo_survey_page.url)

        self.assertContains(response, molo_survey_page.title)
        self.assertContains(response, molo_survey_page.intro)
        self.assertContains(response, molo_survey_form_field.label)

        response = self.client.post(molo_survey_page.url, {
            molo_survey_form_field.label.lower().replace(' ', '-'): 'python'
        })
        self.assertContains(response, molo_survey_page.thank_you_text)
        self.assertContains(response, 'Results')
        self.assertContains(response, molo_survey_form_field.label)
        self.assertContains(response, 'python</span> 1')

    def test_multi_step_option(self):
        molo_survey_page, molo_survey_form_field = \
            self.create_molo_survey_page(
                parent=self.section_index,
                allow_anonymous_submissions=True,
                multi_step=True
            )

        extra_molo_survey_form_field = MoloSurveyFormField.objects.create(
            page=molo_survey_page,
            sort_order=2,
            label='Your favourite actor',
            field_type='singleline',
            required=True
        )

        response = self.client.get(molo_survey_page.url)

        self.assertContains(response, molo_survey_page.title)
        self.assertContains(response, molo_survey_page.intro)
        self.assertContains(response, molo_survey_form_field.label)
        self.assertNotContains(response, extra_molo_survey_form_field.label)
        self.assertContains(response, 'Next Question')

        response = self.client.post(molo_survey_page.url + '?p=2', {
            molo_survey_form_field.label.lower().replace(' ', '-'): 'python'
        })

        self.assertContains(response, molo_survey_page.title)
        self.assertContains(response, molo_survey_page.intro)
        self.assertNotContains(response, molo_survey_form_field.label)
        self.assertContains(response, extra_molo_survey_form_field.label)
        self.assertContains(response, 'Submit Survey')

        response = self.client.post(molo_survey_page.url + '?p=3', {
            extra_molo_survey_form_field.label.lower().replace(' ', '-'):
                'Steven Seagal ;)'
        })

        self.assertContains(response, molo_survey_page.thank_you_text)

        # for test_multi_step_multi_submissions_anonymous
        return molo_survey_page.url

    def test_can_submit_after_validation_error(self):
        molo_survey_page, molo_survey_form_field = \
            self.create_molo_survey_page(
                parent=self.section_index,
                allow_anonymous_submissions=True
            )

        response = self.client.get(molo_survey_page.url)

        self.assertContains(response, molo_survey_page.title)
        self.assertContains(response, molo_survey_page.intro)
        self.assertContains(response, molo_survey_form_field.label)

        response = self.client.post(molo_survey_page.url, {})

        self.assertContains(response, 'This field is required.')

        response = self.client.post(molo_survey_page.url, {
            molo_survey_form_field.label.lower().replace(' ', '-'): 'python'
        })

        self.assertContains(response, molo_survey_page.thank_you_text)

    def test_multi_step_multi_submissions_anonymous(self):
        '''
        Tests that multiple anonymous submissions are not allowed for
        multi-step surveys by default
        '''
        molo_survey_page_url = self.test_multi_step_option()

        response = self.client.get(molo_survey_page_url)

        self.assertContains(response,
                            'You have already completed this survey.')

    def test_survey_template_tag_on_home_page(self):
        molo_survey_page, molo_survey_form_field = \
            self.create_molo_survey_page(parent=self.surveys_index)
        response = self.client.get("/")
        self.assertContains(response,
                            'Take The Survey</a>'.format(
                                molo_survey_page.url))
        self.assertContains(response, molo_survey_page.intro)

    def test_translated_survey(self):
        self.user = self.login()
        molo_survey_page, molo_survey_form_field = \
            self.create_molo_survey_page(parent=self.surveys_index)

        self.client.post(reverse(
            'add_translation', args=[molo_survey_page.id, 'fr']))
        translated_survey = MoloSurveyPage.objects.get(
            slug='french-translation-of-test-survey')
        translated_survey.save_revision().publish()

        response = self.client.get("/")
        self.assertContains(response,
                            '<h1 class="surveys__title">Test Survey</h1>')
        self.assertNotContains(
            response,
            '<h1 class="surveys__title">French translation of Test Survey</h1>'
        )

        response = self.client.get('/locale/fr/')
        response = self.client.get('/')
        self.assertNotContains(
            response,
            '<h1 class="surveys__title">Test Survey</h1>')
        self.assertContains(
            response,
            '<h1 class="surveys__title">French translation of Test Survey</h1>'
        )

    def test_survey_template_tag_on_section_page(self):
        molo_survey_page, molo_survey_form_field = \
            self.create_molo_survey_page(parent=self.section)

        response = self.client.get(self.section.url)
        self.assertContains(response,
                            'Take The Survey</a>'.format(
                                molo_survey_page.url))
        self.assertContains(response, molo_survey_page.intro)

    def test_translated_survey_on_section_page(self):
        self.user = self.login()
        molo_survey_page, molo_survey_form_field = \
            self.create_molo_survey_page(parent=self.section)

        self.client.post(reverse(
            'add_translation', args=[molo_survey_page.id, 'fr']))
        translated_survey = MoloSurveyPage.objects.get(
            slug='french-translation-of-test-survey')
        translated_survey.save_revision().publish()

        response = self.client.get(self.section.url)
        self.assertContains(response,
                            '<h1 class="surveys__title">Test Survey</h1>')
        self.assertNotContains(
            response,
            '<h1 class="surveys__title">French translation of Test Survey</h1>'
        )

        response = self.client.get('/locale/fr/')
        response = self.client.get(self.section.url)
        self.assertNotContains(
            response,
            '<h1 class="surveys__title">Test Survey</h1>')
        self.assertContains(
            response,
            '<h1 class="surveys__title">French translation of Test Survey</h1>'
        )

    def test_survey_template_tag_on_article_page(self):
        molo_survey_page, molo_survey_form_field = \
            self.create_molo_survey_page(parent=self.article)
        response = self.client.get(self.article.url)
        self.assertContains(response,
                            'Take The Survey</a>'.format(
                                molo_survey_page.url))
        self.assertContains(response, molo_survey_page.intro)


class TestDeleteButtonRemoved(TestCase, MoloTestCaseMixin):

    def setUp(self):
        self.mk_main()
        self.english = SiteLanguage.objects.create(locale='en')

        self.login()

        self.surveys_index = SurveysIndexPage(
            title='Security Questions',
            slug='security-questions')
        self.main.add_child(instance=self.surveys_index)
        self.surveys_index.save_revision().publish()

    def test_delete_btn_removed_for_surveys_index_page_in_main(self):

        main_page = Main.objects.first()
        response = self.client.get('/admin/pages/{0}/'
                                   .format(str(main_page.pk)))
        self.assertEquals(response.status_code, 200)

        surveys_index_page_title = (
            SurveysIndexPage.objects.first().title)

        soup = BeautifulSoup(response.content, 'html.parser')
        index_page_rows = soup.find_all('tbody')[0].find_all('tr')

        for row in index_page_rows:
            if row.h2.a.string == surveys_index_page_title:
                self.assertTrue(row.find('a', string='Edit'))
                self.assertFalse(row.find('a', string='Delete'))

    def test_delete_button_removed_from_dropdown_menu(self):
        surveys_index_page = SurveysIndexPage.objects.first()

        response = self.client.get('/admin/pages/{0}/'
                                   .format(str(surveys_index_page.pk)))
        self.assertEquals(response.status_code, 200)

        delete_link = ('<a href="/admin/pages/{0}/delete/" '
                       'title="Delete this page" class="u-link '
                       'is-live ">Delete</a>'
                       .format(str(surveys_index_page.pk)))
        self.assertNotContains(response, delete_link, html=True)

    def test_delete_button_removed_in_edit_menu(self):
        surveys_index_page = SurveysIndexPage.objects.first()

        response = self.client.get('/admin/pages/{0}/edit/'
                                   .format(str(surveys_index_page.pk)))
        self.assertEquals(response.status_code, 200)

        delete_button = ('<li><a href="/admin/pages/{0}/delete/" '
                         'class="shortcut">Delete</a></li>'
                         .format(str(surveys_index_page.pk)))
        self.assertNotContains(response, delete_button, html=True)
