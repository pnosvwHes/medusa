from django import template

from app.utils import is_admin

register = template.Library()

@register.filter(name='add_class')
def add_class(field, css):
    return field.as_widget(attrs={"class": css})


@register.filter
def is_admin_user(user):
    if user is None:
        return False
    return is_admin(user)