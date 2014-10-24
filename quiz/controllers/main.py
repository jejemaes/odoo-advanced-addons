# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class QuizController(http.Controller):

    #----------------------------------------------------------
    # Pages
    #----------------------------------------------------------

    @http.route('/quiz', type='http', auth="user")
    def quiz_index(self, **kw):
        """ Display the page with all quiz the current user is a participant """
        pass

    @http.route('/quiz/<model("quiz.quiz"):quiz>', type='http', auth="user")
    def quiz_page(self, quiz_id, **kw):
        """ Display the list of question serie of current quiz """
        pass

    @http.route('/quiz/<model("quiz.quiz"):quiz>/serie/<int:serie_id>', type='http', auth="user")
    def quiz_serie_page(self, quiz, serie_id, **kw):
        """ Display the recevied question, or the buzzer """
        pass

    @http.route('/quiz/admin/<model("quiz.quiz"):quiz>', type='http', auth="user")
    def quiz_admin_page(self, quiz, **kw):
        """ Display the page to adminitrate the quiz """
        return request.render('quiz.quiz_admin_page', {'quiz': quiz})

    #----------------------------------------------------------
    # Actions
    #----------------------------------------------------------

    @http.route('/quiz/buzz', type='json', auth="user")
    def quiz_buzz(self):
        pass

    @http.route('/quiz/answer', type='json', auth="user")
    def quiz_answer(self, question_id, proposition_id):
        pass
