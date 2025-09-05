from django import template
register = template.Library()
from num2fawords import words


@register.filter
def num2words_fa(field):
    try:
        value = field.value()
        if not value:  
            value = field.form.initial.get(field.name)
        if not value and hasattr(field.form, "instance"):  
            value = getattr(field.form.instance, field.name, None)
        if not value:
            return ""
        return words(int(value))
    except Exception:
        return ""