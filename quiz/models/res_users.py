# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResUsers(models.Model):

    _inherit = 'res.users'

    quiz_ids = fields.Many2many('quiz.quiz', 'quiz_quiz_res_user_participants', string='Quizzes')
