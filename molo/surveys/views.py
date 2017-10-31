from __future__ import unicode_literals

import json
from wagtail.wagtailcore.models import Page

from django.views.generic import TemplateView
from molo.surveys.models import MoloSurveyPage, SurveysIndexPage
from molo.core.models import ArticlePage
from django.shortcuts import get_object_or_404, redirect

from wagtail.wagtailcore.utils import cautious_slugify

from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse
from django.shortcuts import render
from django.utils.translation import ugettext as _

from wagtail.wagtailadmin import messages
from wagtail.wagtailadmin.utils import permission_required

from .forms import CSVGroupCreationForm


class SurveySuccess(TemplateView):
    template_name = "surveys/molo_survey_page_landing.html"

    def get_context_data(self, *args, **kwargs):
        context = super(TemplateView, self).get_context_data(*args, **kwargs)
        pages = self.request.site.root_page.get_descendants()
        ids = []
        for page in pages:
            ids.append(page.id)
        survey = get_object_or_404(
            MoloSurveyPage, slug=kwargs['slug'], id__in=ids)
        results = dict()
        if survey.show_results:
            # Get information about form fields
            data_fields = [
                (field.clean_name, field.label)
                for field in survey.get_form_fields()
            ]

            # Get all submissions for current page
            submissions = (
                survey.get_submission_class().objects.filter(page=survey))
            for submission in submissions:
                data = submission.get_data()

                # Count results for each question
                for name, label in data_fields:
                    answer = data.get(name)
                    if answer is None:
                        # Something wrong with data.
                        # Probably you have changed questions
                        # and now we are receiving answers for old questions.
                        # Just skip them.
                        continue

                    if type(answer) is list:
                        # answer is a list if the field type is 'Checkboxes'
                        answer = u', '.join(answer)

                    question_stats = results.get(label, {})
                    question_stats[answer] = question_stats.get(answer, 0) + 1
                    results[label] = question_stats
        if survey.show_results_as_percentage:
            for question, answers in results.items():
                total = sum(answers.values())
                for key in answers.keys():
                    answers[key] = (answers[key] * 100) / total
        context.update({'self': survey, 'results': results})
        return context


def submission_article(request, survey_id, submission_id):
    # get the specific submission entry
    survey_page = get_object_or_404(Page, id=survey_id).specific
    SubmissionClass = survey_page.get_submission_class()

    submission = SubmissionClass.objects.filter(
        page=survey_page).filter(pk=submission_id).first()
    if not submission.article_page:
        survey_index_page = (
            SurveysIndexPage.objects.descendant_of(
                request.site.root_page).live().first())
        body = []
        for value in submission.get_data().values():
            body.append({"type": "paragraph", "value": str(value)})
        article = ArticlePage(
            title='yourwords-entry-%s' % cautious_slugify(submission_id),
            slug='yourwords-entry-%s' % cautious_slugify(submission_id),
            body=json.dumps(body)
        )
        survey_index_page.add_child(instance=article)
        article.save_revision()
        article.unpublish()

        submission.article_page = article
        submission.save()
        return redirect('/admin/pages/%d/move/' % article.id)
    return redirect('/admin/pages/%d/edit/' % submission.article_page.id)


# CSV creation views
@permission_required('auth.add_group')
def create(request):
    group = Group()
    if request.method == 'POST':
        form = CSVGroupCreationForm(
            request.POST, request.FILES, instance=group)
        if form.is_valid():
            form.save()

            messages.success(
                request,
                _("Group '{0}' created. "
                  "Imported {1} user(s).").format(
                    group, group.user_set.count()),
                buttons=[
                    messages.button(reverse('wagtailusers_groups:edit',
                                            args=(group.id,)), _('Edit'))
                ]
            )
            return redirect('wagtailusers_groups:index')

        messages.error(request, _(
            "The group could not be created due to errors."))
    else:
        form = CSVGroupCreationForm(instance=group)

    return render(request, 'csv_group_creation/create.html', {
        'form': form
    })
