import babel
import babel.dates
import pytz
import odoo

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


def format_datetime(env, value, tz=False, dt_format='medium', lang_code=False):
    """ Formats the datetime in a given format.
        :param {str, datetime} value: naive datetime to format either in string or in datetime
        :param {str} tz: name of the timezone  in which the given datetime should be localized
        :param {str} dt_format: one of “full”, “long”, “medium”, or “short”, or a custom date/time pattern compatible with `babel` lib
        :param {str} lang_code: ISO code of the language to use to render the given datetime
    """
    if not value:
        return ''
    if isinstance(value, str):
        timestamp = odoo.fields.Datetime.from_string(value)
    else:
        timestamp = value

    tz_name = tz or env.user.tz or 'UTC'
    utc_datetime = pytz.utc.localize(timestamp, is_dst=False)
    try:
        context_tz = pytz.timezone(tz_name)
        localized_datetime = utc_datetime.astimezone(context_tz)
    except Exception:
        localized_datetime = utc_datetime

    lang = get_lang(env, lang_code)

    locale = babel.Locale.parse(lang.code or lang_code)  # lang can be inactive, so `lang`is empty

    # Babel allows to format datetime in a specific language without change locale
    # So month 1 = January in English, and janvier in French
    # Be aware that the default value for format is 'medium', instead of 'short'
    #     medium:  Jan 5, 2016, 10:20:31 PM |   5 janv. 2016 22:20:31
    #     short:   1/5/16, 10:20 PM         |   5/01/16 22:20
    # Formatting available here : http://babel.pocoo.org/en/latest/dates.html#date-fields
    return babel.dates.format_datetime(localized_datetime, dt_format, locale=locale)
