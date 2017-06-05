from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client

from molo.core.models import SiteLanguageRelation, Main, Languages
from molo.core.tests.base import MoloTestCaseMixin
from molo.surveys.models import (MoloSurveyPage, MoloSurveyFormField,
                                 SurveysIndexPage)

from bs4 import BeautifulSoup

User = get_user_model()


class TestSurveyViews(TestCase, MoloTestCaseMixin):
    def setUp(self):
        self.client = Client()
        self.mk_main()
        self.main = Main.objects.all().first()
        self.language_setting = Languages.objects.create(
            site_id=self.main.get_site().pk)
        self.english = SiteLanguageRelation.objects.create(
            language_setting=self.language_setting,
            locale='en',
            is_active=True)
        self.french = SiteLanguageRelation.objects.create(
            language_setting=self.language_setting,
            locale='fr',
            is_active=True)

        self.section = self.mk_section(self.section_index, title='section')
        self.article = self.mk_article(self.section, title='article')

        # Create surveys index pages
        self.surveys_index = SurveysIndexPage.objects.child_of(
            self.main).first()

        self.user = User.objects.create_user(
            username='tester',
            email='tester@example.com',
            password='tester')

        self.mk_main2()
        self.main2 = Main.objects.all().last()
        self.language_setting2 = Languages.objects.create(
            site_id=self.main2.get_site().pk)
        self.english2 = SiteLanguageRelation.objects.create(
            language_setting=self.language_setting2,
            locale='en',
            is_active=True)
        self.french2 = SiteLanguageRelation.objects.create(
            language_setting=self.language_setting2,
            locale='fr',
            is_active=True)

        self.mk_main2(title='main3', slug='main3', path=00010003)
        self.client2 = Client(HTTP_HOST=self.main2.get_site().hostname)

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
        }, follow=True)

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
        }, follow=True)
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
            }, follow=True)

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
        }, follow=True)
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
        }, follow=True)

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
        }, follow=True)

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

    def test_survey_template_tag_on_home_page_specific(self):
        molo_survey_page, molo_survey_form_field = \
            self.create_molo_survey_page(parent=self.surveys_index)
        response = self.client.get("/")
        self.assertContains(response, 'Take The Survey</a>')
        self.assertContains(response, molo_survey_page.intro)
        user = User.objects.create_superuser(
            username='testuser', password='password', email='test@email.com')
        self.client2.login(user=user)
        response = self.client2.get(self.site2.root_url)
        self.assertNotContains(response, 'Take The Survey</a>')

    def test_can_only_see_sites_surveys_in_admin(self):
        molo_survey_page, molo_survey_form_field = \
            self.create_molo_survey_page(parent=self.surveys_index)
        response = self.client.get("/")
        self.assertContains(response, 'Take The Survey</a>')
        self.assertContains(response, molo_survey_page.intro)
        user = User.objects.create_superuser(
            username='testuser', password='password', email='test@email.com')
        self.client2.login(user=user)
        response = self.client2.get(self.site2.root_url)
        self.assertNotContains(response, 'Take The Survey</a>')
        self.login()
        response = self.client.get('/admin/surveys/')
        self.assertContains(
            response,
            '<h2><a href="/admin/surveys/submissions/%s/">'
            'Test Survey</a></h2>' % molo_survey_page.pk)
        user = get_user_model().objects.create_superuser(
            username='superuser2',
            email='superuser2@email.com', password='pass2')
        self.client2.login(username='superuser2', password='pass2')

        response = self.client2.get(self.site2.root_url + '/admin/surveys/')
        self.assertNotContains(
            response,
            '<h2><a href="/admin/surveys/submissions/%s/">'
            'Test Survey</a></h2>' % molo_survey_page.pk)

    def test_no_duplicate_indexes(self):
        self.assertTrue(SurveysIndexPage.objects.child_of(self.main2).exists())
        self.assertEquals(
            SurveysIndexPage.objects.child_of(self.main2).count(), 1)
        self.client.post(reverse(
            'wagtailadmin_pages:copy',
            args=(self.surveys_index.pk,)),
            data={
                'new_title': 'blank',
                'new_slug': 'blank',
                'new_parent_page': self.main2,
                'copy_subpages': 'true',
                'publish_copies': 'true'})
        self.assertEquals(
            SurveysIndexPage.objects.child_of(self.main2).count(), 1)

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

    def test_survey_template_tag_on_footer(self):
        self.user = self.login()
        molo_survey_page, molo_survey_form_field = \
            self.create_molo_survey_page(parent=self.surveys_index)

        self.client.post(reverse(
            'add_translation', args=[molo_survey_page.id, 'fr']))
        translated_survey = MoloSurveyPage.objects.get(
            slug='french-translation-of-test-survey')
        translated_survey.save_revision().publish()

        response = self.client.get('/')
        self.assertContains(
            response,
            '<a href="/surveys-main-1/test-survey/" class="footer-link">'
            '<img src="/static/img/clipboard.png" width="auto" '
            'class="menu-list__item--icon" />Test Survey</a>', html=True)

        self.client.get('/locale/fr/')
        response = self.client.get('/')
        self.assertContains(
            response,
            '<a href="/surveys-main-1/french-translation-of-test-survey/" '
            'class="footer-link"><img src="/static/img/clipboard.png" '
            'width="auto" class="menu-list__item--icon" />'
            'French translation of Test Survey</a>', html=True)

    def test_survey_template_tag_on_section_page(self):
        molo_survey_page, molo_survey_form_field = \
            self.create_molo_survey_page(parent=self.section)

        response = self.client.get(self.section.url)
        self.assertContains(response, 'Take The Survey</a>')
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

    def test_survey_list_display_direct_logged_out(self):
        molo_survey_page, molo_survey_form_field = \
            self.create_molo_survey_page(
                parent=self.surveys_index,
                display_survey_directly=True)
        response = self.client.get('/')
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'Please log in to take this survey')
        self.assertNotContains(response, molo_survey_form_field.label)

    def test_survey_list_display_direct_logged_in(self):
        molo_survey_page, molo_survey_form_field = \
            self.create_molo_survey_page(
                parent=self.surveys_index,
                display_survey_directly=True)

        self.user = self.login()
        response = self.client.get('/')
        self.assertEquals(response.status_code, 200)
        self.assertNotContains(response, 'Please log in to take this survey')
        self.assertContains(response, molo_survey_form_field.label)

        response = self.client.post(molo_survey_page.url, {
            molo_survey_form_field.label.lower().replace(' ', '-'): 'python'
        }, follow=True)

        self.assertContains(response, molo_survey_page.thank_you_text)

        response = self.client.get('/')
        self.assertNotContains(response, molo_survey_form_field.label)
        self.assertContains(response,
                            'You have already completed this survey.')

    def test_anonymous_submissions_option_display_direct(self):
        molo_survey_page, molo_survey_form_field = \
            self.create_molo_survey_page(
                parent=self.surveys_index,
                display_survey_directly=True,
                allow_anonymous_submissions=True,
            )

        response = self.client.get('/')

        self.assertContains(response, molo_survey_form_field.label)
        response = self.client.post(molo_survey_page.url, {
            molo_survey_form_field.label.lower().replace(' ', '-'): 'python'
        }, follow=True)
        self.assertContains(response, molo_survey_page.thank_you_text)

        response = self.client.get('/')
        self.assertNotContains(response, molo_survey_form_field.label)
        self.assertContains(response,
                            'You have already completed this survey.')

    def test_multiple_submissions_display_direct(self):
        molo_survey_page, molo_survey_form_field = \
            self.create_molo_survey_page(
                parent=self.surveys_index,
                display_survey_directly=True,
                allow_multiple_submissions_per_user=True,
            )

        self.user = self.login()
        response = self.client.post(molo_survey_page.url, {
            molo_survey_form_field.label.lower().replace(' ', '-'): 'python'
        }, follow=True)
        self.assertContains(response, molo_survey_page.thank_you_text)

        response = self.client.get('/')
        self.assertContains(response, molo_survey_form_field.label)
        self.assertNotContains(response,
                               'You have already completed this survey.')


class TestDeleteButtonRemoved(TestCase, MoloTestCaseMixin):

    def setUp(self):
        self.mk_main()
        self.main = Main.objects.all().first()
        self.language_setting = Languages.objects.create(
            site_id=self.main.get_site().pk)
        self.english = SiteLanguageRelation.objects.create(
            language_setting=self.language_setting,
            locale='en',
            is_active=True)

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
