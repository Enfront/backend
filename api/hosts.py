from django_hosts import patterns, host

import os

host_patterns = patterns(
    '',
    host(r'^.*(?=(\.' + os.environ['SITE_URL'] + '))', 'api.suburls', name='wildcard'),
    host(r'', 'api.urls', name=' '),
)
