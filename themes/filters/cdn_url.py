from liquid.filter import string_filter


@string_filter
def cdn_url(media):
    return 'https://jkpay.s3.us-east-2.amazonaws.com' + media
