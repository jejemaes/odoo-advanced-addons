# -*- coding: utf-8 -*-
{
    'name': "Distance Shipping",
    'description': """
Send your shippings by yourself but compute fees with distance
===============================================================

Delivery your products but compute how many kilometer you will have to do.

    """,
    'category': 'Inventory/Delivery',
    'sequence': 330,
    'version': '1.0',
    'depends': ['delivery', 'base_geolocalize'],
    'data': [
        'security/ir.model.access.csv',
        'views/delivery_distance_views.xml',
        'views/res_config_settings_views.xml',
    ],
}
