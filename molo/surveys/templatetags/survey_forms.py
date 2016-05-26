from django import template

from copy import copy

from molo.surveys.models import SurveyPage

register = template.Library()


@register.inclusion_tag('surveys/surveys_list.html',
                        takes_context=True)
def survey_page(context, pk=None, page=None):
    context = copy(context)
    if page:
        context.update({
            'surveys': SurveyPage.objects.live().child_of(page)
        })
    return context
