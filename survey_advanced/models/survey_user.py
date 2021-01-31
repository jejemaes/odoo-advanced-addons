# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SurveyUserInputLine(models.Model):
    _inherit = 'survey.user_input.line'

    answer_char_box = fields.Char(related='question_id.answer_char_box')
    free_text_manual_scoring = fields.Boolean(related='survey_id.free_text_manual_scoring')
    is_reviewed = fields.Boolean("Is reviewed", default=False)

    @api.model
    def _get_answer_score_values(self, vals, compute_speed_score=True):
        """ Hack to allow setting the score manually when correcting free text answer. """
        if 'answer_is_correct' in vals:
            if not vals.get('answer_is_correct'):
                vals.update({
                    'answer_is_correct': False,
                    'answer_score': 0.0,
                    'is_reviewed': True,
                })
                return {}
        if 'answer_score' in vals:
            answer_score = vals.get('answer_score', 0.0)
            vals.update({
                'answer_is_correct': answer_score > 0,
                'answer_score': answer_score,
                'is_reviewed': True,
            })
            return {}

        # normal case: but we need to set auto-corrected answer as reviewed
        result = super(SurveyUserInputLine, self)._get_answer_score_values(vals, compute_speed_score=compute_speed_score)

        is_reviewed = False
        answer_type = vals.get('answer_type')
        question = self.env['survey.question'].browse(int(vals['question_id']))
        if question.question_type in ['simple_choice', 'multiple_choice']:
            if answer_type == 'suggestion':
                is_reviewed = True
        elif question.is_scored_question:
            answer = vals.get('value_%s' % answer_type)
            if answer_type == 'numerical_box':
                answer = float(answer)
            elif answer_type == 'date':
                answer = fields.Date.from_string(answer)
            elif answer_type == 'datetime':
                answer = fields.Datetime.from_string(answer)
            if answer and answer == question['answer_%s' % answer_type]:
                is_reviewed = True

        result['is_reviewed'] = is_reviewed
        return result

    def action_set_uncorrect(self):
        return self._action_set_score(0)

    def action_set_halfcorrect(self):
        return self._action_set_score(0.5)

    def action_set_correct(self):
        return self._action_set_score(1)

    def _action_set_score(self, factor=1):
        for inputline in self:
            max_score = inputline.question_id.answer_score
            inputline.write({
                'answer_score': max_score * factor,
                'is_reviewed': True,
            })
        return True
