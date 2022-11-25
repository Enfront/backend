from liquid.filter import string_filter
from slugify import slugify


@string_filter
def collection_url(collection_name):
    return '/collections/' + slugify(collection_name)
