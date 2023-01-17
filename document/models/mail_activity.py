# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.exceptions import UserError


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    def _domain_activity_type_id(self):
        """ Make the domain customisable, in order to prevent 'upload_document' activity type on document (except on request). """
        active_model = self.env.context.get('default_res_model')
        active_id = self.env.context.get('default_res_id')
        if active_model == 'document.document':
            if not self.env['document.document'].search([('id', '=', active_id), ('document_type', '=', 'request')]).exists():
                return "['&', ('category', '!=', 'upload_file'), '|', ('res_model', '=', False), ('res_model', '=', res_model)]"
        return "['|', ('res_model', '=', False), ('res_model', '=', res_model)]"

    activity_type_id = fields.Many2one(domain=lambda r: r._domain_activity_type_id())

    @api.model_create_multi
    def create(self, vals_list):
        activities = super().create(vals_list)

        document_ids = activities.filtered(lambda a: a.res_model == 'document.document' and a.activity_category == 'upload_file').mapped('res_id')
        if document_ids:
            documents = self.env['document.document'].browse(document_ids)
            if any(document.document_type != 'request' for document in documents):
                raise UserError(_("Can not upload file on document. Only on document request."))

        return activities

    def _action_done(self, feedback=False, attachment_ids=None):
        document = None
        if attachment_ids:

            if len(attachment_ids) != 1:
                raise UserError(_("Can not upload multiple files to answer the document request."))

            activities = self.filtered(lambda activity: activity.res_model == 'document.document')

            if len(activities) == 1:  # don't want to handle other use case
                activity = self[0]
                document = self.env['document.document'].browse(activity.res_id)
                attachment = self.env['ir.attachment'].browse(attachment_ids[0])

                if document.document_type == 'request':
                    document.write({
                        'document_type': 'file',
                        'attachment_id': attachment.id,
                        'res_model': None,
                        'res_id': None,
                    })
                    if not feedback:
                        feedback = _("Document Request: %s Uploaded by: %s") % (document.name, self.env.user.name)

        messages, next_activities = super(MailActivity, self)._action_done(feedback=feedback, attachment_ids=attachment_ids)

        if document:
            self.env['mail.activity'].search([('res_model', '=', document._name), ('res_id', '=', document.id), ('activity_type_id.category', '=', 'upload_file')]).unlink()

        return messages, next_activities
