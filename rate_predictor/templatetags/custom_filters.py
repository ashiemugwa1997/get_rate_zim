from django import template

register = template.Library()

@register.filter(name='mul')
def mul(value, arg):
    """Multiply the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return None

@register.filter(name='sub')
def sub(value, arg):
    """Subtract the argument from the value"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return None

@register.filter(name='div')
def div(value, arg):
    """Divide the value by the argument"""
    try:
        if float(arg) != 0:
            return float(value) / float(arg)
        return None
    except (ValueError, TypeError):
        return None