# -*- coding: utf-8 -*-

import base64
import psycopg2

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.addons.base_import.models.base_import import FIELDS_RECURSION_LIMIT


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.bank.statement.import"

    def _match_csv(self):
        return [bool(self._match_csv_format(attachment.name)) for attachment in self.attachment_ids]

    def _match_csv_format(self, filename):
        return filename and filename.lower().strip().endswith('.csv')

    def import_file(self):
        match_csv = self._match_csv()
        if match_csv and all(match_csv):  # not empty array AND all are csv files
            if len(match_csv) > 1:  # but only one file is accepted
                raise UserError(_('Only one CSV file can be uploaded.'))
            return self._import_csv_file_action()
        return super(AccountBankStatementImport, self).import_file()

    def _import_csv_file_action(self):
        import_wizard = self.env['base_import.import'].create({
            'res_model': 'account.bank.statement.line',
            'file': base64.b64decode(self.attachment_ids[0].datas),
            'file_name': self.attachment_ids[0].name,
            'file_type': 'text/csv'
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'bank_statement_import',
            'params': {
                'model': 'account.bank.statement.line',
                'context': self.env.context,
                'filename': self.attachment_ids.name,
                'import_wizard_id': import_wizard.id,
            }
        }
