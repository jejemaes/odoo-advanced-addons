# -*- coding: utf-8 -*-
{
    'name': "Document Text",
    'summary': "Text Document in DMS",
    'description': """
        Create and edit Text documents.
    """,
    'author': "jejemaes",
    'category': 'Extra Tools',
    'version': '1.0',
    'application': True,
    'depends': ['document'],
    'data': [
        'views/document_views.xml',
        'report/document_text_templates.xml',
        'report/document_text_reports.xml',
    ],
    'qweb': [
        "static/src/xml/document_kanban_controller.xml",
    ],
}
