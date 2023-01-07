# -*- coding: utf-8 -*-

{
    'name': 'HR Planning',
    'category': 'planning',
    'description': """
Handle the planning of your employee
=====================================
- Send and publish plannings to employees
- Allow them to take shifts (collaborative way)
""",
    'depends': ['hr', 'planning'],
    'data': [
        'data/mail_data.xml',
        'security/planning_security.xml',
        'report/planning_shift_templates.xml',
        'report/planning_shift_reports.xml',
        'wizard/planning_send_views.xml',
        'views/planning_planning_templates.xml',
        'views/planning_planning_views.xml',
        'views/planning_shift_views.xml',
        'views/planning_shift_template_views.xml',
        'views/planning_menus.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'planning/static/src/js/planning_frontend_calendar.js',
        ],
    }
}
