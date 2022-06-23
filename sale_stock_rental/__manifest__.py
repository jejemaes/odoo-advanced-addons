# -*- coding: utf-8 -*-

{
    'name': 'Sale Stock Rental',
    'version': '1.0',
    'summary': 'Rent Your Stockable Products',
    'sequence': 30,
    'description': """
Rental Managment for Stock
===========================
For now this module only prevent to create delivery order when confirming rental Sale Items. """,
    'category': 'Rental',
    'depends': ['sale_rental', 'stock'],
    'data': [
        'views/product_views.xml',
        # 'views/rental_views.xml',
        # 'views/sale_order_views.xml',
    ],
    'installable': True,
    'auto_install': True,
}
