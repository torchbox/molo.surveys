from django.conf import settings
from django.utils.html import format_html_join
from django.contrib.auth.models import User

from wagtail.wagtailcore import hooks


@hooks.register('construct_main_menu')
def show_surveys_entries_for_users_have_access(request, menu_items):
    if not request.user.is_superuser and not User.objects.filter(
            pk=request.user.pk, groups__name='Moderators').exists():
        menu_items[:] = [
            item for item in menu_items if item.name != 'surveys']


@hooks.register('insert_global_admin_js')
def global_admin_js():
    js_files = [
        'js/survey-admin.js',
    ]

    js_includes = format_html_join(
        '\n', '<script src="{0}{1}"></script>',
        ((settings.STATIC_URL, filename) for filename in js_files)
    )
    return js_includes
