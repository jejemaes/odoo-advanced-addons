# -*- coding: utf-8 -*-

{
    'name' : 'PoS Restaurant Menu',
    'version' : '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 10,
    'description': """
PoS Restaurant Menu
====================
Online menu with QR Code
Print QR Code Badge for tables

    """,
    'depends' : ['pos_restaurant'],
    'data': [
        'security/pos_restaurant_menu_security.xml',
        'security/ir.model.access.csv',
        'wizard/restaurant_menu_print_qrcode_views.xml',
        'views/pos_restaurant_menu_templates.xml',
        'views/pos_restaurant_menu_views.xml',
        'report/restaurant_menu_qrcode_templates.xml',
        'report/restaurant_menu_qrcode_reports.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
