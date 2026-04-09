from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Получает элемент из словаря по ключу"""
    return dictionary.get(key)

@register.filter
def get_proposed_price(proposal_item):
    """Возвращает предлагаемую цену"""
    if proposal_item:
        return proposal_item.proposed_price
    return ''