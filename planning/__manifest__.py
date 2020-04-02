# -*- coding: utf-8 -*-

{
    'name': 'Planning',
    'category': 'Planning',
    'description': """
Handle the planning of your human resources
============================================
""",
    'depends': ['base_setup', 'web_gantt', 'resource_advanced'],
    'data': [
        'security/planning_security.xml',
        'security/ir.model.access.csv',
        'report/planning_shift_templates.xml',
        'report/planning_shift_reports.xml',
        'wizard/planning_print_views.xml',
        'wizard/planning_shift_generator_views.xml',
        'views/planning_planning_views.xml',
        'views/planning_shift_views.xml',
        'views/planning_shift_template_views.xml',
        'views/planning_menus.xml',
        'views/res_config_settings_views.xml',
    ],
}
