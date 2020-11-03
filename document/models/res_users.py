# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, modules


class Users(models.Model):
    _name = 'res.users'
    _inherit = ['res.users']

    favorite_document_ids = fields.Many2many('document.document', 'document_document_user_favorite_rel', 'user_id', 'document_id', string="Favorites Documents")

    @api.model
    def systray_get_activities(self):
        """ Update the systray icon of ir.attachment activities to use the contact application one instead of base icon. """
        activities = super(Users, self).systray_get_activities()
        for activity in activities:
            if activity['model'] != 'document.document':
                continue
            activity['icon'] = modules.module.get_module_icon('document')
        return activities
