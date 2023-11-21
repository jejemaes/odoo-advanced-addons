# -*- coding: utf-8 -*-
import json
from lxml import etree

from odoo import models, fields, api, _
from odoo.tools.view_validation import get_variable_names


class View(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=[('gantt', "Gantt")], ondelete={'gantt': 'cascade'})

    def _validate_tag_gantt(self, node, name_manager, node_info):
        field_names = []
        for child in node.iterchildren(tag=etree.Element):
            if child.tag == 'field':
                field_names.append(child.get('name'))

        for attr, expr in node.items():
            if attr == 'precision':
                try:
                    dummy = json.loads(expr.replace("'", '"'))
                except Exception as exc:
                    self._raise_view_error("'precision' must be a JSON dict.", node=node, from_exception=exc)

            # inspired from base/models/ir_ui_view.py L1810
            if attr.startswith('decoration-'):
                vnames = get_variable_names(expr)
                if vnames:
                    name_manager.must_have_fields(node, vnames, f"{attr}={expr}")
