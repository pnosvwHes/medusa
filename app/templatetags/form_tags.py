from django import template
from app.utils import is_admin
register = template.Library()
from num2fawords import words
from jalali_date import datetime2jalali


@register.filter(name='add_class')
def add_class(field, css):
    return field.as_widget(attrs={"class": css})


@register.filter
def is_admin_user(user):
    if user is None:
        return False
    return is_admin(user)

@register.filter(name='num2words_fa')
def num2words_fa(value):
    try:
        if not value:
            return ""
        return words(int(value))
    except (ValueError, TypeError):
        return ""



@register.filter
def to_jalali(value, fmt="%Y/%m/%d"):
    if not value:
        return ""
    try:
        return datetime2jalali(value).strftime(fmt)
    except Exception:
        return value