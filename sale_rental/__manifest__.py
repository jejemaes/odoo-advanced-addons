# -*- coding: utf-8 -*-

{
    'name': 'Sale Rental',
    'version': '1.0',
    'summary': 'Rent Your Material',
    'sequence': 30,
    'description': """
Rental Managment
=================
Rent your machines and other resources for money to your customer through Sales Orders, manage your calendar and confirm the rental.
    """,
    'category': 'Rental',
    'depends': ['sale_management', 'rental'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_views.xml',
        'views/rental_views.xml',
        'views/resource_views.xml',
        'views/sale_order_views.xml',
        'views/sale_portal_templates.xml',
        'views/res_config_settings_views.xml',
        'views/rental_menus.xml',
        'report/sale_order_report_templates.xml',
        'wizard/rental_add_product_views.xml',
    ],
    'installable': True,
    'demo': [
        'data/product_demo.xml',
        'data/resource_demo.xml',
    ]
}
