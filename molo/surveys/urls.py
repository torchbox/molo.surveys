
from django.conf.urls import url
from molo.surveys.views import SurveySuccess


urlpatterns = [
    url(
        r"^(?P<slug>[\w-]+)/success/$",
        SurveySuccess.as_view(),
        name="success"
    ),
]
