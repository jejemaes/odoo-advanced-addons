# -*- coding: utf-8 -*-

{
    'name': "Event Advanced",
    'summary': "Advanced options for Events",
    'description': """
        Advanced options for Events:
        - Allow to disable registration
        - Use QRCode on registration
        - ...
    """,
    'author': "jejemaes",
    'category': 'Marketing/Events',
    'version': '1.0',
    'application': False,
    'depends': ['event'],
    'auto_install': True,
    'data': [
        'views/event_event_views.xml',
        'views/event_type_views.xml',
        'views/event_registration_qrcode_templates.xml',
        'report/event_reports.xml',
        'report/event_report_templates.xml',
    ],
}
