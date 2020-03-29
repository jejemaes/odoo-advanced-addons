

# TODO remove me in 13.0
def get_lang(env, lang_code=False):
    """
    Retrieve the first lang object installed, by checking the parameter lang_code,
    the context and then the company. If no lang is installed from those variables,
    fallback on the first lang installed in the system.
    :param str lang_code: the locale (i.e. en_US)
    :return res.lang: the first lang found that is installed on the system.
    """
    langs = [code for code, _ in env['res.lang'].get_installed()]
    for code in [lang_code, env.context.get('lang'), env.user.company_id.partner_id.lang, langs[0]]:
        if code in langs:
            return env['res.lang']._lang_get(code)

# TODO remove me in 13.0
def format_amount(env, amount, currency, lang_code=False):
    fmt = "%.{0}f".format(currency.decimal_places)
    lang = get_lang(env, lang_code)

    formatted_amount = lang.format(fmt, currency.round(amount), grouping=True, monetary=True)\
        .replace(r' ', u'\N{NO-BREAK SPACE}').replace(r'-', u'-\N{ZERO WIDTH NO-BREAK SPACE}')

    pre = post = u''
    if currency.position == 'before':
        pre = u'{symbol}\N{NO-BREAK SPACE}'.format(symbol=currency.symbol or '')
    else:
        post = u'\N{NO-BREAK SPACE}{symbol}'.format(symbol=currency.symbol or '')

    return u'{pre}{0}{post}'.format(formatted_amount, pre=pre, post=post)

