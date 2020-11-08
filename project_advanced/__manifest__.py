# -*- coding: utf-8 -*-

{
    'name': "Project Advanced",
    'summary': """Gantt View for Tasks, ... """,
    'description': """

    """,
    "category": "Project",
    'author': "jejemaes",
    'license': "GPL-3",
    'version': '1.1',

    'depends': ['web_view_gantt', 'project'],
    'data': [
        'security/ir.model.access.csv',
        'security/project_advanced_security.xml',
        'views/project_views.xml',
        'views/project_template_views.xml',
        'views/res_config_settings_views.xml',
    ],
}
