
from django.conf.urls import url
from molo.surveys.views import SurveySuccess


urlpatterns = [
    url(
        r"^success/(?P<pk>\d+)/$",
        SurveySuccess.as_view(),
        name="success"
    ),
]
