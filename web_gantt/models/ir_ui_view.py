# -*- coding: utf-8 -*-

from odoo import models, fields, api


class View(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=[('gantt', "Gantt")], ondelete={'gantt': 'cascade'})

    # def _postprocess_access_rights(self, model, node):
    #     super(View, self)._postprocess_access_rights(model, node)

    #     Model = self.env[model]
    #     is_base_model = self.env.context.get('base_model_name', model) == model

    #     if node.tag == 'gantt':
    #         for action, operation in (('create', 'create'), ('delete', 'unlink'), ('edit', 'write')):
    #             if (not node.get(action) and
    #                     not Model.check_access_rights(operation, raise_exception=False) or
    #                     not self._context.get(action, True) and is_base_model):
    #                 node.set(action, 'false')

    #     return node


class ActWindowView(models.Model):
    _inherit = 'ir.actions.act_window.view'

    view_mode = fields.Selection(selection_add=[('gantt', "Gantt")], ondelete={'gantt': 'cascade'})
