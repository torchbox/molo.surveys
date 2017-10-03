from django.core.paginator import Paginator
from django.utils.functional import cached_property


class SkipLogicPaginator(Paginator):
    def __init__(self, object_list):
        super(SkipLogicPaginator, self).__init__(object_list, per_page=1)
        self.skip_indexes = [
            i + 1 for i, field in enumerate(self.object_list) if field.has_skipping
        ]
        self.skip_indexes = [0] + self.skip_indexes + [self.object_list.count()]

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
