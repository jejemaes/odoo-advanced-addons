# -*- coding: utf-8 -*-

import base64
import psycopg2

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.addons.base_import.models.base_import import FIELDS_RECURSION_LIMIT


class AccountBankStmtImportCSV(models.TransientModel):

    _inherit = 'base_import.import'

    def _parse_import_data(self, data, import_fields, options):
        data = super(AccountBankStmtImportCSV, self)._parse_import_data(data, import_fields, options)
        statement_id = self._context.get('force_bank_statement_id')
        if statement_id:
            import_fields.append('statement_id/.id')
            import_fields.append('sequence')

            for index, line in enumerate(data):
                line.append(statement_id)
                line.append(index)
        return data

    def execute_import(self, fields, columns, options, dryrun=False):
        result = {}
        if options.get('importing_bank_statement', False):
            self._cr.execute('SAVEPOINT import_bank_statement')

            statement = self.env['account.bank.statement'].create(self._prepare_bank_statement_values())
            result = super(AccountBankStmtImportCSV, self.with_context(force_bank_statement_id=statement.id)).execute_import(fields, columns, options, dryrun=dryrun)

            try:
                if dryrun:
                    self._cr.execute('ROLLBACK TO SAVEPOINT import_bank_statement')
                else:
                    self._cr.execute('RELEASE SAVEPOINT import_bank_statement')
                    result['messages'].append({
                        'statement_id': statement.id,
                        'type': 'bank_statement'
                    })
            except psycopg2.InternalError:
                pass

            # set the real end balance with the theorical one
            balance_end = statement.read(['balance_end'])['balance_end']
            statement.write({'balance_end_real': balance_end})
        else:
            result = super(AccountBankStmtImportCSV, self).execute_import(fields, columns, options, dryrun=dryrun)
        return result

    def _prepare_bank_statement_values(self):
        return  {
            'journal_id': self._context.get('journal_id', False),
            'reference': self.file_name
        }
