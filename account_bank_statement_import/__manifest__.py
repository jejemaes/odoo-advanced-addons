# -*- encoding: utf-8 -*-
{
    'name': 'Account Bank Statement Import',
    'category': 'Accounting/Accounting',
    'version': '1.0',
    'depends': ['account'],
    'author': "jejemaes",
    'description': """
Generic Wizard to Import Bank Statements.

(This module does not include any type of import format.)

OFX and QIF imports are available in Enterprise version.""",
    'data': [
        'security/ir.model.access.csv',
        'views/account_bank_statement_import_view.xml',
        'data/account_import_tip_data.xml',
    ],
    'demo': [
        'data/partner_bank_demo.xml',
    ],
    'installable': True,
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'account_bank_statement_import/static/src/**/*',
        ],
    },
}
