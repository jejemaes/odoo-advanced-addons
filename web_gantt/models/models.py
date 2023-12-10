# -*- coding: utf-8 -*-

from lxml.builder import E
from odoo import models, api
from odoo.osv import expression


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

    @api.model
    def gantt_read(self, domain, fields, groupby, offset=0, limit=None):
        # TODO check access read
        # combine domaine with access rules

        # read group
        limit = min(80, limit or 80)
        raw_groups = self.read_group(domain, fields=fields + ['__record_ids:array_agg(id)'], groupby=groupby, offset=offset, limit=limit, lazy=False)

        # sanitize groups
        record_ids = set()
        for raw_group in raw_groups:
            raw_group.pop('__count', None)
            raw_group.pop('__domain', None)
            record_ids = record_ids.union(set(raw_group['__record_ids']))
            raw_group['__record_ids'].sort()

        # read records
        record_domain = expression.AND([domain, [('id', 'in', list(record_ids))]])
        record_fields = list(set(fields + groupby))
        records = self.search_read(record_domain, record_fields, order="id")

        return {
            'length': len(raw_groups),
            'records': records,
            'groups': raw_groups,
        }
