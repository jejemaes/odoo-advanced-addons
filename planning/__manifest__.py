# -*- coding: utf-8 -*-

{
    'name': 'Planning',
    'category': 'planning',
    'description': """
Handle the planning of your employee or other resources
=======================================================
""",
    'depends': ['hr', 'web_view_gantt', 'resource_advanced'],
    'data': [
        #'views/assets.xml',
        'security/planning_security.xml',
        'security/ir.model.access.csv',
        'views/planning_views.xml',
        'views/planning_menus.xml',
    ],
    'qweb': ['static/src/xml/gallery_import.xml'],

}
