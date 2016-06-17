from django import template

from copy import copy

from molo.surveys.models import MoloSurveyPage, SurveysIndexPage

register = template.Library()


@register.inclusion_tag('surveys/surveys_list.html', takes_context=True)
def surveys_list(context, pk=None):
    context = copy(context)
    locale_code = context.get('locale_code')
    page = SurveysIndexPage.objects.live().first()
    if page:
        surveys = (
            MoloSurveyPage.objects.live().child_of(page).filter(
                languages__language__is_main_language=True).specific())
    else:
        surveys = []

    context.update({
        'surveys': [
            a.get_translation_for(locale_code) or a for a in surveys]
    })
    return context


@register.inclusion_tag('surveys/surveys_list.html', takes_context=True)
def surveys_list_for_pages(context, pk=None, page=None):
    context = copy(context)
    locale_code = context.get('locale_code')
    if page:
        surveys = (
            MoloSurveyPage.objects.live().child_of(page).filter(
                languages__language__is_main_language=True).specific())
    else:
        surveys = []

    context.update({
        'surveys': [
            a.get_translation_for(locale_code) or a for a in surveys]
    })
    return context
