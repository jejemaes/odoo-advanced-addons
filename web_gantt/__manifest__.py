# -*- coding: utf-8 -*-
{
    'name': "Web DHX Gantt",
    'summary': """Gantt View using dhtmlx""",
    'description': """

    """,
    "category": "Tools",
    'author': "jejemaes",
    'license': "GPL-3",
    'version': '1.1',
    'depends': ['web'],
    'assets': {
        'web.assets_backend': [
            'web_gantt/static/src/scss/gantt.scss',
            'web_gantt/static/src/js/gantt_utils.js',
            'web_gantt/static/src/js/gantt_renderer.js',
            'web_gantt/static/src/js/gantt_model.js',
            'web_gantt/static/src/js/gantt_controller.js',
            'web_gantt/static/src/js/gantt_view.js',
            'web_gantt/static/src/js/gantt_row.js',
        ],
        'web.assets_qweb': [
            'web_gantt/static/src/xml/web_gantt.xml',
        ],
    }
}
