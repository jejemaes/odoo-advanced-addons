# -*- coding: utf-8 -*-

{
    'name': 'Website Sale Rental',
    'version': '1.0',
    'summary': 'Rental in your eCommerce',
    'sequence': 30,
    'description': """
Rental Managment
=================
Rent your machines and other resources for money to your customer through your eCommerce.
    """,
    'category': 'Rental',
    'depends': ['sale_rental', 'website_sale'],
    'data': [
        'security/ir.model.access.csv',
        'security/website_sale_rental_security.xml',
        'views/website_sale_templates.xml',
        'views/product_template_views.xml',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_frontend': [
            'website_sale_rental/static/src/js/website_sale_rental.js',
        ],
        'web.assets_qweb': [
            'website_sale_rental/static/src/xml/website_sale_rental_modal.xml',
        ],
    },
    'installable': False,
}
