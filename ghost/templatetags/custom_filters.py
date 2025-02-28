from django import template

register = template.Library()

@register.filter
def calcular_id(counter, i):
	return counter * 3 - i

@register.filter
def calcular_id_bomxop(counter, i):
	return counter * 6 - i

@register.filter
def get_attr(obj, attr):
    """Retorna um atributo de um objeto ou chave de um dicionário."""
    if isinstance(obj, dict):
        return obj.get(attr, "")
    return getattr(obj, attr, "")