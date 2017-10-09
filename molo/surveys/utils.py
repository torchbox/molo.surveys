from __future__ import unicode_literals

from django.core.paginator import Paginator, Page
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.utils.functional import cached_property
from django.utils.text import slugify

from .blocks import SkipState


class SkipLogicPaginator(Paginator):
    def __init__(self, object_list, data=dict()):
        self.data = data
        super(SkipLogicPaginator, self).__init__(object_list, per_page=1)
        self.skip_indexes = [
            i + 1 for i, field in enumerate(self.object_list) if field.has_skipping
        ]
        if self.skip_indexes:
            self.skip_indexes = [0] + self.skip_indexes + [self.object_list.count()]
        else:
            self.skip_indexes = range(self.object_list.count() + 1)

    def _get_page(self, *args, **kwargs):
        return SkipLogicPage(*args, **kwargs)

    @cached_property
    def num_pages(self):
        return len(self.skip_indexes) - 1

    def page_skip_values(self):
        minimum_skip = self.num_pages
        next_question_index = 0
        question_ids = [question.id for question in self.object_list]
        if self.last_question_page:
            last_question = self.object_list[self.last_question_page]
            last_answer = self.data[last_question.clean_name]
            if last_question.is_next_action(last_answer, SkipState.QUESTION):
                next_question_id = last_question.next_page(last_answer)
                next_question_index = question_ids.index(next_question_id)
                minimum_skip = next(i-1 for i, v in enumerate(self.skip_indexes) if v > next_question_index)

        return minimum_skip, next_question_index

    @cached_property
    def last_question_page(self):
        question_labels = [question.clean_name for question in self.object_list]
        answered_questions = [
            question_labels.index(question) for question in self.data if question in question_labels
        ]
        if answered_questions:
            return max(answered_questions)

        return 0

    def page(self, number):
        number = self.validate_number(number)
        if self.last_question_page == number:
            minimum_skip, next_question_index = self.page_skip_values()
        else:
            minimum_skip, next_question_index = self.num_pages, 0

        bottom_index = min(number - 1, minimum_skip)
        top_index = bottom_index + self.per_page
        bottom = max(self.skip_indexes[bottom_index], next_question_index)
        top = self.skip_indexes[top_index]
        return self._get_page(self.object_list[bottom:top], bottom_index + 1, self)


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
