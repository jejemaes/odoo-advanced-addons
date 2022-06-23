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
        'views/assets.xml',
        'views/website_sale_templates.xml',
        'views/product_template_views.xml',
        #'views/sale_order_views.xml',
        #'report/sale_order_report_templates.xml',
    ],
    'installable': True,
    'auto_install': True,
}
