# -*- coding: utf-8 -*-

{
    'name': "Project Template",
    'summary': """Template for Projects""",
    'description': """

    """,
    "category": "Project",
    'author': "jejemaes",
    'license': "GPL-3",
    'version': '1.1',

    'depends': ['project'],
    'data': [
        'security/ir.model.access.csv',
        'views/project_views.xml',
        'views/project_template_views.xml',
    ],
    'installable': True,
}
