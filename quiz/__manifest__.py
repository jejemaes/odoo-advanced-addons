# -*- coding: utf-8 -*-
{
    'name': 'Quizz',
    'version': '1.0',
    'author': 'jejemaes.net',
    'category': 'Games',
    'description': """
Quizz
=====
This modules provides the basics of quizz module, including
    * Web Buzzer page
    * Team and concurrence buzzing
    * Counting points
    """,
    'website': 'https://www.jejemaes.net',
    'depends': ['base_setup', 'bus', 'portal'],
    'data': [
        'views/quiz_quiz_views.xml',
        'views/quiz_quiz_templates.xml',
        'data/quiz_quiz_data.xml'
    ],
    'qweb': [],
    'demo': [
        'data/quiz_quiz_demo.xml'
    ],
    'installable': True,
    'auto_install': False,
}
