from django import template

register = template.Library()

@register.filter
def calcular_id(counter, i):
	return counter * 3 - i