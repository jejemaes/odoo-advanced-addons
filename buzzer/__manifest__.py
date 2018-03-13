# -*- coding: utf-8 -*-
{
    'name': 'Buzzer',
    'version': '1.0',
    'author': 'jejemaes.net',
    'category': 'Games',
    'description': """
Quizz
=====
This modules provides the buzzer features: log as portal user on 'buzz' channel and then player can buzz.
    """,
    'website': 'https://www.jejemaes.net',
    'depends': ['base_setup', 'bus', 'portal'],
    'data': [
        'security/ir.model.access.csv',
        'security/buzzer_security.xml',
        'views/assets.xml',
        'views/buzzer_templates.xml',
        'views/buzzer_views.xml',
    ],
    'qweb': [
        'static/src/xml/buzzer.xml',
    ],
    'installable': True,
    'auto_install': False,
}
