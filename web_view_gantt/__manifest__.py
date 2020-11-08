# -*- coding: utf-8 -*-
{
    'name': "Web View DHX Gantt",
    'summary': """Gantt View using dhtmlx""",
    'description': """

    """,
    "category": "Tools",
    'author': "jejemaes",
    'license': "GPL-3",
    'version': '1.1',

    'depends': ['web'],

    # always loaded
    'data': [
        'views/assets.xml',
    ],
    'qweb': [
        "static/src/xml/web_gantt.xml",
    ],
}
