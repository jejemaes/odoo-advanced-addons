# -*- coding: utf-8 -*-

{
    "name": "Sale Event Advanced",
    "version": "1.0",
    "category": "Marketing",
    'summary': "Advanced options when Selling Events",
    'description': """
        Advanced options to sell Events:
        - Quantity on registration
        - ...
    """,
    "depends": ["event_sale", "event_advanced"],
    "data": [
        'wizards/event_edit_registration.xml'
    ],
    "installable": False,
    "auto_install": True,
}
