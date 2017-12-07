from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import TestCase, RequestFactory
from django.test.client import Client

from wagtail_personalisation.rules import UserIsLoggedInRule

from molo.core.models import (
    ArticlePage,
    ArticlePageTags,
    Main,
    SectionPage,
    Tag,
)
from molo.core.tests.base import MoloTestCaseMixin

from molo.surveys.adapters import (
    get_rule,
    index_rules_by_type,
    transform_into_boolean_list,
    evaluate,
    PersistentSurveysSegmentsAdapter,
)
from molo.surveys.models import MoloSurveyPageView, SegmentUserGroup

from molo.surveys.rules import GroupMembershipRule


class TestAdapterUtils(TestCase, MoloTestCaseMixin):
    def setUp(self):
        self.client = Client()
        self.mk_main()
        self.main = Main.objects.all().first()

        self.request_factory = RequestFactory()
        self.request = self.request_factory.get('/')
        self.request.user = get_user_model().objects.create_user(
            username='tester', email='tester@example.com', password='tester')

        self.group_1 = SegmentUserGroup.objects.create(name='Group 1')
        self.group_2 = SegmentUserGroup.objects.create(name='Group 2')

        self.request.user.segment_groups.add(self.group_1)

        self.group_rule_1 = GroupMembershipRule(group=self.group_1)
        self.group_rule_2 = GroupMembershipRule(group=self.group_2)
        self.logged_in_rule = UserIsLoggedInRule(is_logged_in=True)

    def test_get_rule(self):
        fake_ds = {
            'TimeRule': ['first time rule', 'second time rule'],
            'UserIsLoggedInRule': ['first logged in rule']
        }

        self.assertEqual(get_rule('TimeRule_0', fake_ds),
                         fake_ds["TimeRule"][0])
        self.assertEqual(get_rule('TimeRule_1', fake_ds),
                         fake_ds["TimeRule"][1])
        self.assertEqual(get_rule('UserIsLoggedInRule_0', fake_ds),
                         fake_ds["UserIsLoggedInRule"][0])

    def test_index_rules_by_type(self):
        test_input = [self.logged_in_rule,
                      self.group_rule_1,
                      self.group_rule_2]
        expected_output = {
            'GroupMembershipRule': [self.group_rule_1, self.group_rule_2],
            'UserIsLoggedInRule': [self.logged_in_rule]
        }

        self.assertEqual(
            index_rules_by_type(test_input),
            expected_output)

    def test_transform_into_boolean_list_simple(self):
        sample_stream_data = [
            {u'type': u'Rule', u'value': u'UserIsLoggedInRule_0'},
            {u'type': u'Operator', u'value': u'and'},
            {
                u'type': u'NestedLogic',
                u'value': {
                    u'operator': u'or',
                    u'rule_1': u'GroupMembershipRule_0',
                    u'rule_2': u'GroupMembershipRule_1'}
            }
        ]

        sample_indexed_rules = {
            'GroupMembershipRule': [self.group_rule_1, self.group_rule_2],
            'UserIsLoggedInRule': [self.logged_in_rule]
        }

        self.assertEqual(
            transform_into_boolean_list(
                sample_stream_data,
                sample_indexed_rules,
                self.request
            ),
            [self.logged_in_rule.test_user(self.request),
             u'and',
             [
                self.group_rule_1.test_user(self.request),
                u'or',
                self.group_rule_2.test_user(self.request)
            ]]
        )

    def test_transform_into_boolean_list_only_nested(self):
        sample_stream_data = [
            {
                u'type': u'NestedLogic',
                u'value': {
                    u'operator': u'or',
                    u'rule_1': u'UserIsLoggedInRule_0',
                    u'rule_2': u'GroupMembershipRule_0'}
            }
        ]

        sample_indexed_rules = {
            'GroupMembershipRule': [self.group_rule_1],
            'UserIsLoggedInRule': [self.logged_in_rule]
        }

        self.assertEqual(
            transform_into_boolean_list(
                sample_stream_data,
                sample_indexed_rules,
                self.request
            ),
            [[
                self.logged_in_rule.test_user(self.request),
                u'or',
                self.group_rule_1.test_user(self.request)
            ]]
        )

    def test_evaluate_1(self):
        self.assertEqual(
            (False or True),
            evaluate([False, "or", True])
        )

    def test_evaluate_2(self):
        self.assertEqual(
            (False and True or True),
            evaluate([False, "and", True, "or", True])
        )

    def test_evaluate_3(self):
        self.assertEqual(
            (False and True),
            evaluate([False, "and", True])
        )

    def test_evaluate_4(self):
        self.assertEqual(
            ((False or True) and True),
            evaluate([[False, "or", True], "and", True])
        )

    def test_evaluate_5(self):
        self.assertEqual(
            ((False or True) and (False and False)),
            evaluate([[False, "or", True], "and", [False, "and", False]])
        )

    def test_evaluate_6(self):
        self.assertEqual(
            ((False or
                (True or False)) and
             (False and False)),
            evaluate(
                [[False, "or",
                    [True, "or", False]], "and",
                 [False, "and", False]])
        )

    def test_evaluate_7(self):
        self.assertEqual(
            ((False or True) and
             (False and False) or
             (True and False)),
            evaluate(
                [[False, "or", True], "and",
                 [False, "and", False], "or",
                 [True, 'and', False]])
        )

    def test_evaluate_8(self):
        self.assertEqual(
            ((False or True)),
            evaluate(
                [[False, "or", True]])
        )


class TestPersistentSurveysSegmentsAdapter(TestCase, MoloTestCaseMixin):
    def setUp(self):
        self.mk_main()
        self.request = RequestFactory().get('/')
        session_middleware = SessionMiddleware()
        session_middleware.process_request(self.request)
        self.request.session.save()

        self.section = SectionPage(title='test section')
        self.section_index.add_child(instance=self.section)

        self.tags = [Tag(title='tag one'), Tag(title='tag two')]
        for tag in self.tags:
            self.tag_index.add_child(instance=tag)
            tag.save_revision()

        self.page = ArticlePage(title='test article')
        self.section.add_child(instance=self.page)
        self.page.save_revision()

        for tag in self.tags:
            ArticlePageTags.objects.create(
                tag=tag,
                page=self.page,
            )

        self.adapter = PersistentSurveysSegmentsAdapter(self.request)

    def test_no_exception_raised_if_user_not_set(self):
        try:
            self.adapter.add_page_visit(self.page)
        except AttributeError as e:
            self.fail('add_page_visit() raised AttributeError: {0}'.format(e))

    def test_no_pageview_stored_if_not_articlepage(self):
        self.adapter.add_page_visit(self.section)
        self.assertEqual(MoloSurveyPageView.objects.all().count(), 0)

    def test_no_pageview_stored_for_anonymous_user(self):
        self.adapter.add_page_visit(self.page)
        self.assertEqual(MoloSurveyPageView.objects.all().count(), 0)

    def test_pageview_stored_for_each_tag(self):
        self.request.user = self.login()
        self.adapter.add_page_visit(self.page)

        pageviews = MoloSurveyPageView.objects.all()

        self.assertEqual(pageviews.count(), 2)

        self.assertEqual(pageviews[0].user, self.request.user)
        self.assertEqual(pageviews[0].tag, self.tags[0])
        self.assertEqual(pageviews[0].page, self.page)
        self.assertEqual(pageviews[1].tag, self.tags[1])
