# -*- coding: utf-8 -*-

{
    'name': "Survey Advanced",
    'summary': """Score free text answer, ... """,
    'description': """

    """,
    'category': 'Marketing/Surveys',
    'author': "jejemaes",
    'license': "GPL-3",
    'version': '1.0',

    'depends': ['survey',],
    'data': [
        'security/ir.model.access.csv',
        'views/survey_question_views.xml',
        'views/survey_user_views.xml',
        'views/survey_views.xml',
        'views/survey_templates_user_input_session.xml',
        'views/survey_media_views.xml',
        'wizard/audio_importer_views.xml',
    ],
}
