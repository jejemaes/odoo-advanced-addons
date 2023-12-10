# -*- coding: utf-8 -*-

{
    'name' : 'PoS Restaurant Kitchen',
    'version' : '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 10,
    'description': """
PoS Restaurant Kitchen
=======================
This module gives the ability to have kitchen and send order parts to kitchen in order to manage their
preparation. New access group "Cooker" is provide to allow cooker to see order line on an auto
refreshing kanban view.
    """,
    'depends' : ['pos_restaurant'],
    'data': [
        'security/pos_restaurant_kitchen_security.xml',
        'security/ir.model.access.csv',
        'views/pos_order_views.xml',
        'views/pos_config_views.xml',
        'views/pos_restaurant_kitchen_views.xml',
        'views/pos_order_templates.xml',
        'data/pos_restaurant_kitchen_data.xml',
    ],
    'installable': False,
    'application': False,
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            'pos_restaurant_kitchen/static/src/js/autorefresh_kanban_view.js',
            'pos_restaurant_kitchen/static/src/js/printer_fix.js',
            'pos_restaurant_kitchen/static/src/js/print_widget.js',
        ],
        'point_of_sale.assets': [
            'pos_restaurant_kitchen/static/src/scss/pos_restaurant_kitchen.scss'
        ]
    }
}
