# -*- coding: utf-8 -*-

{
    'name': 'Import CSV Bank Statement',
    'category': 'Accounting/Accounting',
    'version': '1.0',
    'depends': ['base_import', 'account_bank_statement_import'],
    'data': [
        'wizard/account_bank_statement_import_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'account_bank_statement_import_csv/static/src/**/*',
        ],
    }
}
