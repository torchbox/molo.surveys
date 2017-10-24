from django import template

from copy import copy
from wagtail.wagtailcore.models import Page
from molo.surveys.models import MoloSurveyPage, SurveysIndexPage

from molo.core.templatetags.core_tags import get_pages
from django.shortcuts import get_object_or_404

register = template.Library()


def get_survey_list(context,
                    only_linked_surveys=False,
                    only_direct_surveys=False,
                    only_yourwords=False):
    if only_linked_surveys and only_direct_surveys:
        raise ValueError('arguments "only_linked_surveys" and '
                         '"only_direct_surveys" cannot both be True')

    context = copy(context)
    locale_code = context.get('locale_code')
    main = context['request'].site.root_page
    page = SurveysIndexPage.objects.child_of(main).live().first()
    if page:
        surveys = []
        if only_linked_surveys:
            surveys = (MoloSurveyPage.objects.child_of(page)
                       .filter(languages__language__is_main_language=True,
                               display_survey_directly=False,
                               your_words_competition=False)
                       .specific())
        elif only_direct_surveys:
            surveys = (MoloSurveyPage.objects.child_of(page)
                       .filter(languages__language__is_main_language=True,
                               display_survey_directly=True,
                               your_words_competition=False)
                       .specific())
        elif only_yourwords:
            surveys = (MoloSurveyPage.objects.child_of(page)
                       .filter(languages__language__is_main_language=True,
                               your_words_competition=True)
                       .specific())
        else:
            surveys = (MoloSurveyPage.objects.child_of(page)
                       .filter(languages__language__is_main_language=True)
                       .specific())
    else:
        surveys = MoloSurveyPage.objects.none()
    context.update({
        'surveys': get_pages(context, surveys, locale_code)
    })
    return context


def add_form_objects_to_surveys(context):
    surveys = []
    for survey in context['surveys']:
        form = None
        if (survey.allow_multiple_submissions_per_user or
                not survey.has_user_submitted_survey(
                    context['request'], survey.id)):
            form = survey.get_form()

        surveys.append({
            'molo_survey_page': survey,
            'form': form,
        })

    context.update({
        'surveys': surveys,
    })

    return context


@register.inclusion_tag('surveys/surveys_headline.html', takes_context=True)
def surveys_list_headline(context):
    return get_survey_list(context)


@register.inclusion_tag('surveys/surveys_list.html', takes_context=True)
def surveys_list(context, pk=None, only_linked_surveys=False,
                 only_direct_surveys=False, only_yourwords=False):
    context = get_survey_list(context,
                              only_linked_surveys=only_linked_surveys,
                              only_direct_surveys=only_direct_surveys,
                              only_yourwords=only_yourwords)
    return add_form_objects_to_surveys(context)


@register.simple_tag(takes_context=True)
def get_survey_list_for_site(context):
    context = copy(context)
    main = context['request'].site.root_page
    page = SurveysIndexPage.objects.child_of(main).live().first()
    if page:
        return (
            MoloSurveyPage.objects.child_of(page).filter(
                languages__language__is_main_language=True).specific())
    return None


@register.simple_tag(takes_context=True)
def submission_has_article(context, survey_id, submission_id):
    survey_page = get_object_or_404(Page, id=survey_id).specific
    SubmissionClass = survey_page.get_submission_class()
    submission = SubmissionClass.objects.filter(
        page=survey_page).filter(pk=submission_id).first()
    if submission.article_page is None:
        return False
    return True


@register.inclusion_tag('surveys/surveys_list.html', takes_context=True)
def surveys_list_for_pages(context, pk=None, page=None):
    context = copy(context)
    locale_code = context.get('locale_code')
    if page:
        surveys = (
            MoloSurveyPage.objects.child_of(page).filter(
                languages__language__is_main_language=True).specific())
    else:
        surveys = MoloSurveyPage.objects.none()

    context.update({
        'surveys': get_pages(context, surveys, locale_code)
    })
    return add_form_objects_to_surveys(context)
