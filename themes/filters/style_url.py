import os

from liquid.filter import string_filter, with_environment
from slugify import slugify


@string_filter
@with_environment
def style_url(asset_name, environment):
    theme_template_path = os.path.join(
        'themes',
        'templates',
        'official',
        slugify(environment.globals['theme'].name),
        'assets',
        'css'
    )

    return 'https://jkpay.s3.us-east-2.amazonaws.com/' + theme_template_path + '/' + asset_name
