from django.test import TestCase
from molo.core.tests.base import MoloTestCaseMixin
from molo.surveys.models import (
    MoloSurveyFormField,
    MoloSurveyPage,
)

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
        self.fourth_field = MoloSurveyFormField.objects.create(
            page=self.survey,
            sort_order=4,
            label='A random animal',
            field_type='singleline',
            required=True
        )
        field_choices = ['next', 'end', 'question']
        self.second_field = MoloSurveyFormField.objects.create(
            page=self.survey,
            sort_order=2,
            label='Your favourite animal',
            field_type='dropdown',
            skip_logic=skip_logic_data(
                field_choices,
                field_choices,
                question=self.fourth_field,
            ),
            required=True
        )
        self.third_field = MoloSurveyFormField.objects.create(
            page=self.survey,
            sort_order=3,
            label='Your least favourite animal',
            field_type='dropdown',
            skip_logic=skip_logic_data(
                field_choices,
                field_choices,
                question=self.fourth_field,
            ),
            required=True
        )
        self.paginator = SkipLogicPaginator(self.survey.get_form_fields())

    def test_correct_num_pages(self):
        self.assertEqual(self.paginator.num_pages, 3)

    def test_skip_indexes_correct(self):
        self.assertEqual(self.paginator.skip_indexes, [0, 2, 3, 4])

    def test_first_page_correct(self):
        page = self.paginator.page(1)
        self.assertEqual(
            page.object_list,
            [self.first_field, self.second_field],
        )
        self.assertTrue(page.has_next())

    def test_second_page_correct(self):
        page = self.paginator.page(2)
        self.assertEqual(page.object_list, [self.third_field])
        self.assertTrue(page.has_next())

    def test_last_page_correct(self):
        last_page = self.paginator.page(3)
        self.assertEqual(last_page.object_list, [self.fourth_field])
        self.assertFalse(last_page.has_next())

    def test_is_end_if_skip_logic(self):
        paginator = SkipLogicPaginator(
            self.survey.get_form_fields(),
            {self.second_field.clean_name: 'end'}
        )
        first_page = paginator.page(1)
        self.assertFalse(first_page.has_next())

    def test_skip_question_if_skip_logic(self):
        paginator = SkipLogicPaginator(
            self.survey.get_form_fields(),
            {self.second_field.clean_name: 'question'}
        )
        page = paginator.page(1)
        next_page_number = page.next_page_number()
        self.assertEqual(next_page_number, 3)
        second_page = paginator.page(next_page_number)
        self.assertEqual(second_page.object_list, [self.fourth_field])

    def test_previous_page_if_skip_a_page(self):
        paginator = SkipLogicPaginator(
            self.survey.get_form_fields(),
            {
                self.first_field.clean_name: 'python',
                self.second_field.clean_name: 'question',
            }
        )
        page = paginator.page(1)
        next_page_number = page.next_page_number()
        self.assertEqual(next_page_number, 3)
        second_page = paginator.page(next_page_number)
        previous_page_number = second_page.previous_page_number()
        self.assertEqual(previous_page_number, 1)
        self.assertEqual(
            paginator.page(previous_page_number).object_list,
            [self.first_field, self.second_field],
        )

    def test_question_progression_index(self):
        paginator = SkipLogicPaginator(
            self.survey.get_form_fields(),
            {
                self.first_field.clean_name: 'python',
                self.second_field.clean_name: 'question',
            }
        )
        self.assertEqual(paginator.previous_question_page, 1)
        self.assertEqual(paginator.last_question_index, 1)
        self.assertEqual(paginator.next_question_page, 3)
        self.assertEqual(paginator.next_question_index, 3)

    def test_no_data_index(self):
        paginator = SkipLogicPaginator(self.survey.get_form_fields())
        self.assertEqual(paginator.previous_question_page, 1)
        self.assertEqual(paginator.last_question_index, 0)
        self.assertEqual(paginator.next_question_page, 1)
        self.assertEqual(paginator.next_question_index, 0)

    def test_single_question_quiz_with_skip_logic_pages_correctly(self):
        self.first_field.delete()
        self.third_field.delete()
        self.fourth_field.delete()
        paginator = SkipLogicPaginator(self.survey.get_form_fields())
        self.assertEqual(paginator.num_pages, 1)


class SkipLogicPaginatorMulti(TestCase, MoloTestCaseMixin):
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
        field_choices = ['next', 'next']
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
            label='Your least favourite animal',
            field_type='singleline',
            required=True
        )
        self.paginator = SkipLogicPaginator(self.survey.get_form_fields())

    def test_correct_num_pages(self):
        self.assertEqual(self.paginator.num_pages, 3)

    def test_skip_indexes_correct(self):
        self.assertEqual(self.paginator.skip_indexes, [0, 1, 2, 3])

    def test_first_page_correct(self):
        self.assertEqual(
            self.paginator.page(1).object_list,
            [self.first_field],
        )

    def test_middle_page_correct(self):
        self.assertEqual(
            self.paginator.page(2).object_list,
            [self.second_field],
        )

    def test_last_page_correct(self):
        last_page = self.paginator.page(3)
        self.assertEqual(last_page.object_list, [self.last_field])
        self.assertFalse(last_page.has_next())
