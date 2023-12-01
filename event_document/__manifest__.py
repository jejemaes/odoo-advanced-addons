# -*- coding: utf-8 -*-

{
    'name': "Event Document",
    'summary': "Document Management System, in Events",
    'description': """
        Upload, manage and share your Documents related to Events
    """,
    'author': "jejemaes",
    'category': 'Extra Tools',
    'version': '1.0',
    'application': False,
    'depends': ['document', 'event_advanced'],
    'auto_install': True,
    'data': [
        'security/event_document_security.xml',
        'views/res_config_settings_views.xml',
        'views/event_event_views.xml',
    ],
}
