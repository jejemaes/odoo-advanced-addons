# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class SurveyQuestion(models.Model):
    _inherit = 'survey.question'

    sequence = fields.Integer(default=1)
    free_text_manual_scoring = fields.Boolean(related='survey_id.free_text_manual_scoring')
    answer_char_box = fields.Char("Correct Text Answer")

    audio_attachment_id = fields.Many2one('ir.attachment', 'Audio File', domain=[('mimetype', 'ilike', 'audio')])
    audio_autoplay = fields.Boolean("Autoplay", default=False)
    audio_file_url = fields.Char(compute='_compute_audio_file_url')

    def name_get(self):
        if self._context.get('question_name_include_seq'):
            return [(question.id, _('%s. %s') % (question.sequence, question.title)) for question in self]
        return super(SurveyQuestion, self).name_get()

    @api.depends('question_type', 'scoring_type', 'answer_date', 'answer_datetime', 'answer_numerical_box', 'survey_id.free_text_manual_scoring')
    def _compute_is_scored_question(self):
        super(SurveyQuestion, self)._compute_is_scored_question()
        for question in self:
            if question.is_scored_question is None or question.scoring_type == 'no_scoring':
                question.is_scored_question = False
            elif question.question_type == 'char_box':
                question.is_scored_question = bool(question.answer_char_box)

    @api.depends('audio_attachment_id')
    def _compute_audio_file_url(self):
        for question in self:
            if question.audio_attachment_id:
                question.audio_file_url = '/web/content/%s?access_token=%s' % (question.audio_attachment_id.id, question.audio_attachment_id.access_token)
            else:
                question.audio_file_url = None

    def _onchange_audio_attachment_id(self):
        if not self.audio_attachment_id:
            self.audio_autoplay = False
        else:
            self.audio_autoplay = True

    def _get_stats_summary_data(self, user_input_lines):
        stats = {}
        if self.question_type in ['char_box', 'text_box']:
            stats['right_inputs_count'] = len(user_input_lines.filtered(lambda line: line.answer_is_correct).mapped('user_input_id'))
        else:
            stats = super(SurveyQuestion, self)._get_stats_summary_data(user_input_lines)
        return stats
