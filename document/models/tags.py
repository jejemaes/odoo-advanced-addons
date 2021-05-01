# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.osv import expression


class Categories(models.Model):
    _name = "document.facet"
    _description = "Facet"
    _order = "sequence, name"

    name = fields.Char("Name", required=True, translate=True)
    folder_id = fields.Many2one('document.folder', string="Folder", required=False, ondelete="cascade")
    tag_ids = fields.One2many('document.tag', 'facet_id', string="Tags")
    tooltip = fields.Char("Tooltip", help="Hover Text Description")
    sequence = fields.Integer("Sequence", default=10)
    color = fields.Integer("Color", default=0)

    _sql_constraints = [
        ('name_unique', 'UNIQUE(folder_id, name)', "Facet already exists in this folder"),
    ]


class Tags(models.Model):
    _name = "document.tag"
    _description = "Tag"
    _order = "sequence, name"
    _rec_name = 'name'

    name = fields.Char("Name", required=True, translate=True)
    folder_id = fields.Many2one('document.folder', string="Folder", related='facet_id.folder_id', store=True, readonly=False)
    facet_id = fields.Many2one('document.facet', string="Category", ondelete='cascade', required=True)
    sequence = fields.Integer("Sequence", default=10)
    color = fields.Integer("Color", related='facet_id.color', readonly=False, store=True)

    _sql_constraints = [
        ('facet_name_unique', 'UNIQUE (facet_id, name)', "Tag already exists for this facet"),
    ]

    def name_get(self):
        if self._context.get('hierarchical_naming'):
            result = []
            for record in self:
                result.append((record.id, "%s: %s" % (record.facet_id.name, record.name)))
            return result
        return super(Tags, self).name_get()

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        args = list(args or [])
        domain = []
        if not (name == '' and operator == 'ilike'):
            domain = [(self._rec_name, operator, name)]
        if (name or '').strip() and operator in ['like', 'ilike', 'not like', 'not ilike']:
            domain = expression.OR([[('facet_id.name', operator, name)], domain])
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
