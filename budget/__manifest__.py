# -*- coding: utf-8 -*-

{
    'name': 'Budget Management',
    'category': 'Budget',
    'description': """
Use budgets to compare actual with expected revenues and costs
--------------------------------------------------------------
""",
    'depends': ['analytic'],
    'data': [
        'security/budget_security.xml',
        'security/ir.model.access.csv',
        'views/analytic_views.xml',
        'views/budget_views.xml',
        'report/budget_print_report_templates.xml',
        'report/budget_print_reports.xml',
    ],
    'demo': ['data/budget_demo.xml'],
    'application': True,

}
