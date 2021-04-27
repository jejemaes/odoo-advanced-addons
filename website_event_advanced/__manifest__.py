# -*- coding: utf-8 -*-

{
    'name': "Website Event Advanced",
    'summary': "Advanced options for Website Event",
    'description': """
        Advanced options for Events
    """,
    'author': "jejemaes",
    'category': 'Marketing/Events',
    'version': '1.0',
    'application': False,
    'depends': ['event_advanced', 'website_event'],
    'auto_install': True,
    'data': [
        'views/event_event_views.xml',
        'views/event_templates.xml',
    ],
}
