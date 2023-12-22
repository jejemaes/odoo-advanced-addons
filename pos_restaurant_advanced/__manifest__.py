# -*- coding: utf-8 -*-

{
    'name' : 'PoS Restaurant Advanced',
    'version' : '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 80,
    'description': """
PoS Restaurant Advanced
=======================
Wizard to create multiple table on a floor plan

    """,
    'depends' : ['pos_restaurant'],
    'data': [
        'security/ir.model.access.csv',
        'views/restaurant_table_views.xml',
        'wizard/restaurant_table_generator_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
