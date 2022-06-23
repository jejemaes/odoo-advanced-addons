# -*- coding: utf-8 -*-

{
    'name': 'Planning',
    'category': 'planning',
    'description': """
Handle the planning of your employee or other resources
=======================================================
""",
    'depends': ['hr', 'web_gantt', 'resource_advanced'],
    'data': [
        'data/mail_data.xml',
        'security/planning_security.xml',
        'security/ir.model.access.csv',
        'report/planning_shift_templates.xml',
        'report/planning_shift_reports.xml',
        'wizard/planning_send_views.xml',
        'wizard/planning_print_views.xml',
        'wizard/planning_shift_generator_views.xml',
        'views/planning_planning_templates.xml',
        'views/planning_planning_views.xml',
        'views/planning_shift_views.xml',
        'views/planning_shift_template_views.xml',
        'views/planning_menus.xml',
        'views/res_config_settings_views.xml',
        'views/assets.xml',
    ],
    'qweb': ['static/src/xml/gallery_import.xml'],
}
