# -*- coding: utf-8 -*-

from odoo import api, fields, models


class Company(models.Model):
    _inherit = 'res.company'

    document_default_tag_ids = fields.Many2many('document.tag', string="Default Tags", domain=[('folder_id', '=', False)])
