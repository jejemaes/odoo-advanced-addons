# -*- coding: utf-8 -*-
import base64
from os import listdir
from os.path import isfile, isdir, join

from odoo import api, fields, models


class Survey(models.Model):
    _inherit = 'survey.survey'

    free_text_manual_scoring = fields.Boolean("Manual review for free answers")
    anwser_to_review_count = fields.Integer("User Free Answer to Review", compute='_compute_anwser_to_review_count')

    @api.depends('user_input_ids.user_input_line_ids.is_reviewed')
    def _compute_anwser_to_review_count(self):
        grouped_data = self.env['survey.user_input.line'].read_group([('survey_id', 'in', self.ids), ('is_reviewed', '=', False), ('question_id.save_as_nickname', '=', False)], ['survey_id'], ['survey_id'])
        mapped_data = {db['survey_id'][0]: db['survey_id_count'] for db in grouped_data}
        for survey in self:
            survey.anwser_to_review_count = mapped_data.get(survey.id, 0)

    @api.onchange('scoring_type')
    def _onchange_scoring_type(self):
        if self.scoring_type == 'no_scoring':
            self.free_text_manual_scoring = False


    def make_blindtest(self):

        self.write({
            'questions_layout': 'page_per_question',
            'progression_mode': 'percent',
            'questions_selection': 'all',
            'users_can_go_back': False,
            'scoring_type': 'scoring_with_answers',
            'free_text_manual_scoring': True,
        })

        mypath = '/home/jerome/Music/blindtest/'

        sequence = 10
        for f in sorted(listdir(mypath)):
            if isfile(join(mypath, f)) and f.endswith('.mp3'):
                with open(join(mypath, f), 'rb') as content_file:
                    data = content_file.read()
                    b64_data = base64.encodebytes(data)
                    attachment = self.env['ir.attachment'].create({
                        'name': f,
                        'datas': b64_data,
                    })
                    attachment.generate_access_token()
                    self.env['survey.question'].create({
                        'title': "Quel est le titre et l'artiste de cette chanson ?",
                        'survey_id': self.id,
                        'question_type': 'char_box',
                        'answer_char_box': attachment.name.replace('-30seconds', ' ')[5:],
                        'audio_attachment_id': attachment.id,
                        'audio_autoplay': True,
                        'is_scored_question': True,
                        'answer_score': 10,
                        'sequence': sequence,
                    })
            elif isdir(join(mypath, f)):
                self.env['survey.question'].create({
                    'title': f,
                    'survey_id': self.id,
                    'is_page': True,
                })
                sequence = self._make_blindtest_subdir(join(mypath, f), sequence)
            sequence += 1


    def _make_blindtest_subdir(self, mypath, sequence):
        for f in sorted(listdir(mypath)):
            if isfile(join(mypath, f)) and f.endswith('.mp3'):
                with open(join(mypath, f), 'rb') as content_file:
                    data = content_file.read()
                    b64_data = base64.encodebytes(data)
                    attachment = self.env['ir.attachment'].create({
                        'name': f,
                        'datas': b64_data,
                    })
                    attachment.generate_access_token()
                    self.env['survey.question'].create({
                        'title': "Quel est le titre et l'artiste de cette chanson ?",
                        'survey_id': self.id,
                        'question_type': 'char_box',
                        'answer_char_box': attachment.name.replace('-30seconds', ' ')[5:],
                        'audio_attachment_id': attachment.id,
                        'audio_autoplay': True,
                        'is_scored_question': True,
                        'answer_score': 10,
                        'sequence': sequence,
                    })
                    sequence += 1
        return sequence
