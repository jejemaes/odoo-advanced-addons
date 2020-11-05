# -*- coding: utf-8 -*-
import base64

from odoo import api, fields, models


class AudioImporter(models.TransientModel):
    _name = 'survey.audio.import'
    _description = 'Audio Importer'

    line_ids = fields.One2many('survey.audio.import.line', 'wizard_id', string='Lines')

    def action_import(self):
        attachment_value_list = []
        for wizard in self:
            for line in wizard.line_ids:
                mimetype = self.env['ir.attachment']._compute_mimetype({'raw': line.content})
                attachment_value_list.append({
                    'name': line.name,
                    'raw': line.content,
                    'type': 'binary',
                    'description': line.name,
                    'mimetype': mimetype,
                })
        attachments = self.env['ir.attachment'].create(attachment_value_list)
        attachments.generate_access_token()
        return True

class AudioImporterLine(models.TransientModel):
    _name = 'survey.audio.import.line'
    _description = 'Audio Importer Line'

    wizard_id = fields.Many2one('survey.audio.import', 'Wizard', required=True)
    content = fields.Binary('File')
    name = fields.Char('Name')
