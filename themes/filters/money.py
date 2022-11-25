from liquid.filter import string_filter, with_environment


@string_filter
@with_environment
def money(amount, environment):
    return str(environment.globals['currency']) + str(format(int(amount) / 100, '.02f'))
