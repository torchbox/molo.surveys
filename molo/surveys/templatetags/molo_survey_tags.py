from django import template

from copy import copy

from molo.surveys.models import MoloSurveyPage, SurveysIndexPage

from molo.core.templatetags.core_tags import get_pages

register = template.Library()


def get_survey_list(context):
    context = copy(context)
    locale_code = context.get('locale_code')
    main = context['request'].site.root_page
    page = SurveysIndexPage.objects.child_of(main).live().first()
    if page:
        surveys = (
            MoloSurveyPage.objects.child_of(page).filter(
                languages__language__is_main_language=True).specific())
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
def surveys_list(context, pk=None):
    context = get_survey_list(context)
    return add_form_objects_to_surveys(context)


@register.simple_tag(takes_context=True)
def get_survey_list_for_site(context):
    context = copy(context)
    locale_code = context.get('locale_code')
    main = context['request'].site.root_page
    page = SurveysIndexPage.objects.child_of(main).live().first()
    if page:
        surveys = (
            MoloSurveyPage.objects.child_of(page).filter(
                languages__language__is_main_language=True).specific())
    else:
        surveys = MoloSurveyPage.objects.none()

    return get_pages(context, surveys, locale_code)


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
