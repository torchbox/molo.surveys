
from wagtail.wagtailcore import hooks
from django.contrib.auth.models import User


@hooks.register('construct_main_menu')
def show_surveys_entries_for_users_have_access(request, menu_items):
    if not request.user.is_superuser and not User.objects.filter(
            pk=request.user.pk, groups__name='Moderators').exists():
        menu_items[:] = [
            item for item in menu_items if item.name != 'surveys']
