# -*- coding: utf-8 -*-
from odoo import api, fields, models


class QuizSerieRel(models.Model):

    _name = 'quiz.serie.relation'
    _description = 'Membership of serie for a quiz'
    _table = 'quiz_quiz_quiz_serie_rel'
    _order = 'sequence'

    quiz_id = fields.Many2one('quiz.quiz', string='Quiz', required=True)
    serie_id = fields.Many2one('quiz.serie', string='Serie', required=True)
    state = fields.Selection([
        ('open', 'open'),
        ('running', 'Running'),
        ('closed', 'Closed'),
    ], string='Status', copy=False, default='open')
    sequence = fields.Integer(string="Sequence", default=5)
    question_count = fields.Integer(string="# of questions", related="serie_id.question_count")


class Quiz(models.Model):

    _name = 'quiz.quiz'
    _description = 'Quiz'

    @api.model
    def _default_stage_id(self):
        stage = self.env['quiz.stage'].search([], limit=1)
        if stage:
            return stage
        return False

    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Note')
    color = fields.Integer('Color Index')
    stage_id = fields.Many2one('quiz.stage', 'Stage', track_visibility='onchange', select=True, default=_default_stage_id)
    user_ids = fields.Many2many('res.users', 'quiz_quiz_res_user_participants', string='Participants')
    user_count = fields.Integer(string="# of user", compute='_compute_user_count')
    serie_rel_ids = fields.One2many('quiz.serie.relation', 'quiz_id', string='Serie Relations')
    serie_ids = fields.Many2many('quiz.serie', 'quiz_quiz_quiz_serie_rel', 'quiz_id', 'serie_id', string='Series', help="Series composing the quiz")
    serie_count = fields.Integer(string="# of serie", compute='_compute_serie_count')

    @api.multi
    def _compute_user_count(self):
        for quiz in self:
            quiz.user_count = len(quiz.user_ids)

    @api.multi
    def _compute_serie_count(self):
        self.env.cr.execute("""
            SELECT quiz_id, count(*)
            FROM quiz_quiz_quiz_serie_rel
            WHERE quiz_id IN %s
            GROUP BY quiz_id
        """, (tuple(self.ids),))
        data = dict(self.env.cr.fetchall())
        for quiz in self:
            quiz.serie_count = data.get(quiz.id, 0)

    #----------------------------------------------------------
    # Quiz Frontend Methods
    #----------------------------------------------------------
    @api.multi
    def action_start(self):
        self.ensure_one()
        stage_id = self.env.ref('quiz.quiz_stage_running').id
        self.write({'stage_id': stage_id})
        return {
            'type': 'ir.actions.act_url',
            'url': '/quiz/admin/%s' % (self.id,),
            'target': 'new',
        }


# class QuizEvent(models.Model):

#     _name = 'quiz.event'
#     _description = 'Quiz Event to sent/received from or to Buzzer'

#     serie_id = fields.Many2one('quiz.serie', string='Quiz', required=True)
#     event_type = fields.Selection([
#         ('update', 'Update'),
#         ('reset', 'Reset'),
#         ('pushed', 'Pushed'),
#         ('question', 'Question'),
#     ], string='Type', default='reset', readonly=True, required=True)
#     content = fields.Text('Message content', required=True)
#     user_ids = fields.Many2many('res.users', 'quiz_event_res_user_rel', string='Users')

class QuizStage(models.Model):

    _name = 'quiz.stage'
    _description = 'Quiz Stage'
    _order = 'sequence'

    name = fields.Char(string='Name', required=True)
    sequence = fields.Integer(string='Sequence', default=5)
    fold = fields.Boolean('Folded in Quizz Kanban')


class QuizSerie(models.Model):

    _name = 'quiz.serie'
    _description = 'Quiz Serie'
    _rec_name = 'name'

    name = fields.Char(string='Name', required=True)
    serie_type = fields.Selection([
        ('buzzer', 'Buzzer'),
        ('chrono', 'Chrono'),
        ('multiple_choice', 'Multiple Choice Question'),
    ], string='Type', default='buzzer', required=True)
    quiz_ids = fields.Many2many('quiz.quiz', 'quiz_quiz_quiz_serie_rel', 'serie_id', 'quiz_id', string='Quiz', help="Quiz in which the serie is used")
    #event_ids = fields.One2many('quiz.event', 'serie_id', string='Events')
    question_ids = fields.One2many('quiz.question', 'serie_id', string='Questions')
    question_count = fields.Integer(string="# of questions", compute='_compute_question_count')

    @api.multi
    def _compute_question_count(self):
        question_data = self.env['quiz.question'].read_group([('serie_id', 'in', self.ids)], ['serie_id'], ['serie_id'])
        mapped_data = dict([(m['serie_id'][0], m['serie_id_count']) for m in question_data])
        for quiz in self:
            quiz.question_count = mapped_data.get(quiz.id, 0)


class QuizQuestion(models.Model):

    _name = 'quiz.question'
    _description = 'Quiz Question'
    _rec_name = 'name'
    _order = 'sequence,create_date'

    name = fields.Char(name='Question', required=True)
    sequence = fields.Integer('Sequence', default=5)
    serie_id = fields.Many2one('quiz.serie', string='Serie', required=True)
    #serie_type = fields.Selection(related='serie_id.serie_type', readonly=True)
    proposition_ids = fields.One2many('quiz.proposition', 'question_id', string='Propositions')
    proposition_count = fields.Integer(string="# of proposition", compute='_compute_proposition_count')

    @api.multi
    def _compute_proposition_count(self):
        proposition_data = self.env['quiz.proposition'].read_group([('question_id', 'in', self.ids)], ['question_id'], ['question_id'])
        mapped_data = dict([(m['question_id'][0], m['question_id_count']) for m in proposition_data])
        for question in self:
            question.proposition_count = mapped_data.get(question.id, 0)


class QuizProposition(models.Model):

    _name = 'quiz.proposition'
    _description = 'Quiz Proposition'
    _rec_name = 'name'
    _order = 'sequence,create_date'

    name = fields.Char(name='Title', required=True)
    question_id = fields.Many2one('quiz.question', string='Question', required=True)
    point = fields.Integer('Point', default=0)
    sequence = fields.Integer('Sequence', default=5)


class QuizAnswer(models.Model):

    _name = 'quiz.user.answer'
    _description = 'Quiz User Answer'

    user_id = fields.Many2one('res.userss', string='User', required=True)
    proposition_id = fields.Many2one('quiz.proposition', string='Proposition', required=True)
    quiz_id = fields.Many2one('quiz.quiz', string='Quiz', required=True)

    # TODO : add constraints
