# -*- coding: utf-8 -*-
{
    'name': "Websie Sale Event Advanced",
    'category': 'Website/Website',
    'summary': "Sell event tickets online (advanced)",
    'description': """
        Advanced options to sell Events:
        - Quantity on registration
        - Allow ticket to be pre-ordered (no SO generated). Usefull to allow customers to pay during the event.
        - ...
    """,
    'sequence': 330,
    'version': '1.0',
    'depends': ['sale_event_advanced', 'website_event_sale'],
    'auto_install': True,
    'data': [
        'views/event_ticket_views.xml',
        'views/event_registration_views.xml',
        'views/event_registration_page_templates.xml',
    ],
}
