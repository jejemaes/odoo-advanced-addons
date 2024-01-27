# -*- coding: utf-8 -*-

{
    'name': 'Budget',
    'category': 'Budget',
    'description': """
Use budgets to compare actual with expected revenues and costs
--------------------------------------------------------------
""",
    'depends': ['mail'],
    'data': [
        'security/budget_security.xml',
        'security/ir.model.access.csv',
        'views/budget_category_views.xml',
        'views/budget_line_views.xml',
        'views/budget_views.xml',
        'report/budget_print_report_templates.xml',
        'report/budget_print_reports.xml',
    ],
    'demo': ['data/budget_demo.xml'],
    'application': True,
    'license': 'LGPL-3',
    'assets': {
        'web.report_assets_common': [
            'budget/static/src/scss/budget_report.scss',
        ],
    }
}
