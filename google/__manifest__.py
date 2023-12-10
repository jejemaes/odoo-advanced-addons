# -*- coding: utf-8 -*-

{
    'name': 'Google OAuth',
    'category': 'Extra Tools',
    'description': """
The module provide the OAuth2 flow for Google APIs
==================================================
""",
    'depends': ['base_setup'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
    ],
    'installable': False,
}
