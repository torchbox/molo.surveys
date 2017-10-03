from django.test import TestCase
from molo.core.tests.base import MoloTestCaseMixin
from molo.surveys.models import MoloSurveyPage, MoloSurveySubmission, MoloSurveyFormField

from ..utils import SkipLogicPaginator
from .utils import skip_logic_data


class TestSkipLogicPaginator(TestCase, MoloTestCaseMixin):
    def setUp(self):
        self.mk_main()
        self.survey = MoloSurveyPage(
            title='Test Survey',
            slug='test-survey',
        )
        self.section_index.add_child(instance=self.survey)
        self.survey.save_revision().publish()
        self.first_field = MoloSurveyFormField.objects.create(
            page=self.survey,
            sort_order=1,
            label='Your other favourite animal',
            field_type='singleline',
            required=True
        )
        field_choices = ['next', 'end']
        self.second_field = MoloSurveyFormField.objects.create(
            page=self.survey,
            sort_order=2,
            label='Your favourite animal',
            field_type='dropdown',
            skip_logic=skip_logic_data(field_choices, field_choices),
            required=True
        )
        self.last_field = MoloSurveyFormField.objects.create(
            page=self.survey,
            sort_order=3,
            label='Your other favourite animal',
            field_type='singleline',
            required=True
        )
        self.paginator = SkipLogicPaginator(self.survey.get_form_fields())

    def test_correct_num_pages(self):
        self.assertEqual(self.paginator.num_pages, 2)

    def test_skip_indexes_correct(self):
        self.assertEqual(self.paginator.skip_indexes, [0, 2, 3])

    def test_first_page_correct(self):
        self.assertEqual(self.paginator.page(1).object_list, [self.first_field, self.second_field])

    def test_last_page_correct(self):
        last_page = self.paginator.page(2)
        self.assertEqual(last_page.object_list, [self.last_field])
        self.assertFalse(last_page.has_next())
