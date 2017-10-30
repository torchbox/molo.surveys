from __future__ import unicode_literals

from django.core.paginator import Page, Paginator
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.utils.functional import cached_property

from .blocks import SkipState


class SkipLogicPaginator(Paginator):
    def __init__(self, object_list, data=dict()):
        # Create a mutatable version of the query data
        self.data = data.copy()
        super(SkipLogicPaginator, self).__init__(object_list, per_page=1)
        self.page_breaks = [
            i + 1 for i, field in enumerate(self.object_list)
            if field.has_skipping
        ]
        num_questions = self.object_list.count()
        if self.page_breaks:
            self.page_breaks.insert(0, 0)
            if self.page_breaks[-1] != num_questions:
                self.page_breaks.append(num_questions)
        else:
            self.page_breaks = range(num_questions + 1)

    def _get_page(self, *args, **kwargs):
        return SkipLogicPage(*args, **kwargs)

    @cached_property
    def num_pages(self):
        return len(self.page_breaks) - 1

    @cached_property
    def next_question_index(self):
        if self.data:
            question_ids = [
                question.sort_order for question in self.object_list
            ]
            last_question = self.object_list[self.last_question_index]
            last_answer = self.data[last_question.clean_name]
            if last_question.is_next_action(last_answer, SkipState.QUESTION):
                # Sorted or is 0 based in the backend and 1 on the front
                next_question_id = last_question.next_page(last_answer) - 1
                return question_ids.index(next_question_id)
            else:
                return self.last_question_index + 1
        return 0

    @cached_property
    def next_question_page(self):
        return next(
            i for i, v in enumerate(self.page_breaks)
            if v > self.next_question_index
        )

    @cached_property
    def answered_indexes(self):
        question_labels = [
            question.clean_name for question in self.object_list
        ]
        answered = [
            question_labels.index(question) for question in self.data
            if question in question_labels
        ]
        # Add in any checkboxes that we missed
        max_answered = max(answered or [self.page_breaks[1]])
        answered_check_boxes = [
            question
            for question in self.object_list[:max_answered]
            if question.field_type == 'checkbox' and
            question.clean_name not in self.data
        ]
        answered.extend(
            question_labels.index(checkbox.clean_name)
            for checkbox in answered_check_boxes
        )
        # add the missing data
        self.data.update({
            checkbox.clean_name: 'off'
            for checkbox in answered_check_boxes
        })
        return answered

    @cached_property
    def first_last_question_index(self):
        if self.answered_indexes:
            return min(self.answered_indexes)
        return 0

    @cached_property
    def last_question_index(self):
        if self.answered_indexes:
            return max(self.answered_indexes)
        return 0

    @cached_property
    def previous_question_page(self):
        return next(
            i for i, v in enumerate(self.page_breaks)
            if v > self.last_question_index
        )

    def page(self, number):
        number = self.validate_number(number)
        index = number - 1
        if not self.data:
            top_index = index + self.per_page
            bottom = self.page_breaks[index]
            top = self.page_breaks[top_index]
        elif self.previous_question_page == number:
            bottom = self.first_last_question_index
            top = self.last_question_index + 1
        else:
            index = self.next_question_page - 1
            bottom = self.next_question_index
            top_index = index + self.per_page
            top = self.page_breaks[top_index]
        return self._get_page(self.object_list[bottom:top], index + 1, self)


class SkipLogicPage(Page):
    def has_next(self):
        return super(SkipLogicPage, self).has_next() and not self.is_end()

    @cached_property
    def last_question(self):
        return self.object_list[-1]

    @cached_property
    def last_response(self):
        return self.paginator.data[self.last_question.clean_name]

    def is_next_action(self, *actions):
        try:
            question_response = self.last_response
        except KeyError:
            return False
        return self.last_question.is_next_action(question_response, *actions)

    def is_end(self):
        return self.is_next_action(SkipState.END, SkipState.SURVEY)

    def success(self, slug):
        if self.is_next_action(SkipState.SURVEY):
            return redirect(
                self.last_question.next_page(self.last_response).url
            )
        return redirect(
            reverse('molo.surveys:success', args=(slug, ))
        )

    def next_page_number(self):
        return self.paginator.next_question_page

    def previous_page_number(self):
        return self.paginator.previous_question_page
