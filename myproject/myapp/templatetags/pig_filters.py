from django import template

register = template.Library()

@register.filter
def age_display(age_months):
    """Convert age in months to years and months format"""
    if age_months >= 12:
        years = age_months // 12
        remaining_months = age_months % 12
        if remaining_months > 0:
            return f"{years} years {remaining_months} months"
        else:
            return f"{years} years"
    else:
        return f"{age_months} months"
