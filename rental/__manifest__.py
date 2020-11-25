# -*- coding: utf-8 -*-
{
    'name': 'Rental',
    'version': '1.0',
    'summary': 'Manage your rental bookings',
    'sequence': 30,
    'description': """
Rental Managment
=================
Rent your machines and other resources, manage your calendar and confirm the rental.
    """,
    'category': 'Rental',
    'depends': ['web_view_gantt', 'resource_advanced', 'mail'],
    'data': [
        'data/sequence_data.xml',
        'data/resource_data.xml',
        'security/rental_security.xml',
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/rental_views.xml',
        'views/rental_menus.xml',
    ],
    'installable': True,
    'application': True,
    'demo': [
        'data/resource_demo.xml',
        'data/rental_demo.xml',
    ],
}
