from liquid.filter import string_filter
from slugify import slugify


@string_filter
def product_url(product_name):
    return '/products/' + slugify(product_name)
