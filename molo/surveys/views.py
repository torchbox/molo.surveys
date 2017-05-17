from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from molo.surveys.models import MoloSurveyPage


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
        context.update({'self': survey, 'results': results})
        return context
