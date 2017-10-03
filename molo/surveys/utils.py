from __future__ import unicode_literals

from django.core.paginator import Paginator, Page
from django.utils.functional import cached_property


class SkipLogicPaginator(Paginator):
    def __init__(self, object_list, data=dict()):
        self.data = data
        super(SkipLogicPaginator, self).__init__(object_list, per_page=1)
        self.skip_indexes = [
            i + 1 for i, field in enumerate(self.object_list) if field.has_skipping
        ]
        self.skip_indexes = [0] + self.skip_indexes + [self.object_list.count()]

    def _get_page(self, *args, **kwargs):
        return SkipLogicPage(*args, **kwargs)

    @cached_property
    def num_pages(self):
        return len(self.skip_indexes) - 1

    def page(self, number):
        number = self.validate_number(number)
        bottom_index = (number - 1)
        top_index = bottom_index + self.per_page
        bottom = self.skip_indexes[bottom_index]
        top = self.skip_indexes[top_index]
        return self._get_page(self.object_list[bottom:top], number, self)


class SkipLogicPage(Page):
    def has_next(self):
        return super(SkipLogicPage, self).has_next() and not self.is_end()

    def is_end(self):
        last_question = self.object_list[-1]
        try:
            question_response = self.paginator.data[last_question.clean_name]
        except KeyError:
            return False
        return last_question.next_action(question_response) == 'end'
