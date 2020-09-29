# -*- coding: utf-8 -*-

{
    'name': 'Budget Analytic',
    'category': 'Budget',
    'description': """
Use budgets to compare actual with expected revenues and costs
--------------------------------------------------------------
""",
    'depends': ['budget', 'analytic'],
    'data': [
        'security/ir.model.access.csv',
        'views/budget_line_views.xml',
        'views/budget_analytic_tag_views.xml',
        'views/analytic_line_views.xml',
        'views/budget_menus.xml',
    ],
    'application': False,
    'license': 'LGPL-3',
}
