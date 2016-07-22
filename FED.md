Running local HTML Tests

To Get Started

- $ virtualenv ve
- $ pip install -e .


- molo scaffold testapp --require molo.surveys --include molo.profiles ^profiles/
- cp local_test_settings.py testapp/testapp/settings/local.py

- cp molo/surveys/test_templates/*.html testapp/testapp/templates/core/

- pip install -e testapp
- py.test --cov=molo.surveys --cov-report=term

- pip install -r requirements-dev.txt
- py.test

To Run A Specific Test
- py.test -k test_survey_template_tag_on_home_page