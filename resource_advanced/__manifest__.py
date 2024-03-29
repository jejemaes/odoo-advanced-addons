# -*- coding: utf-8 -*-

{
    'name': 'Resource Advanced',
    'version': '1.0',
    'summary': '',
    'sequence': 30,
    'description': """
New type of working calendar
=============================
To avoid interval problem with ends of shifts. Allow to define schedule for complete day.
    """,
    'category': 'Hidden',
    'depends': ['resource'],
    'data': [
        'security/ir.model.access.csv',
        'views/resource_views.xml',
        'data/resource_day_data.xml',
    ],
    'auto_install': True,
}
