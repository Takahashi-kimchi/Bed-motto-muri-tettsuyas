# schedule/templatetags/schedule_tags.py

from django import template

# テンプレートライブラリとして登録
register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    辞書から指定されたキーの値を取得するカスタムフィルター
    例: {{ my_dict|get_item:my_key }}
    """
    return dictionary.get(key)