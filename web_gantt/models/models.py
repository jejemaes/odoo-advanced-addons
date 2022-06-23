# -*- coding: utf-8 -*-

from lxml.builder import E
from odoo import models, api


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def _get_default_gantt_view(self):
        """ Generates a default single-line form view using all fields
        of the current model.

        :returns: a form view as an lxml document
        :rtype: etree._Element
        """
        return E.gantt(string=self._description)
