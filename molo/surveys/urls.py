
from django.conf.urls import url
from molo.surveys.views import SurveySuccess, article


urlpatterns = [
    url(
        r"^(?P<slug>[\w-]+)/success/$",
        SurveySuccess.as_view(),
        name="success"
    ),
    url(
        r'^submissions/(\d+)/article/(\d+)/$',
        article, name='article'),
]
