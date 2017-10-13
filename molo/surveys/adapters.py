from collections import defaultdict
import datetime

from wagtail_personalisation.adapters import SessionSegmentsAdapter

from molo.core.models import ArticlePage


class SurveysSegmentsAdapter(SessionSegmentsAdapter):
    def add_page_visit(self, page):
        super(SurveysSegmentsAdapter, self).add_page_visit(page)
        tag_visits = self.request.session.setdefault(
            'tag_count',
            defaultdict(dict),
        )
        if isinstance(page, ArticlePage):
            visit_time = datetime.datetime.utcnow()
            for tag in page.tags.all():
                tag_visits[tag.id][page.path] = visit_time

    def get_tag_count(self, tag, date_from=None, date_to=None):
        """Return the number of visits on the current request or given page"""
        if not date_from:
            date_from = datetime.datetime.min
        if not date_to:
            date_to = datetime.datetime.max

        tag_visits = self.request.session.setdefault(
            'tag_count',
            defaultdict(list),
        )

        visits = tag_visits[tag.id]
        valid_visits = [visit for visit in visits.values()
                        if date_from <= visit <= date_to]
        return len(valid_visits)
