# -*- coding: utf-8 -*-

import base64
import json
import zipfile
import io
import logging

from odoo import http, _
from odoo.exceptions import UserError
from odoo.http import request, content_disposition
from odoo.tools import consteq, replace_exceptions

logger = logging.getLogger(__name__)


class DocumentRoute(http.Controller):

    # ------------------------------------------------------------------
    # Backend Action
    # ------------------------------------------------------------------

    @http.route(['/document/zip_download/<file_ids>'], type='http', auth='user')
    def document_action_backend(self, file_ids, **kwargs):
        zip_name = 'documents-%s' % fields.Date.to_string(fields.Date.today())
        ids_list = [int(x) for x in file_ids.split(',')]
        return self._document_make_zip(zip_name, request.env['document.document'].browse(ids_list).exists())

    @http.route('/document/upload_file', type='http', methods=['POST'], auth="user")
    def document_upload_file(self, ufile, **kwargs):
        document_id = kwargs.get('document_id')
        if not document_id:
            return self._document_upload_files(ufile, **kwargs)
        return self._document_upload_request_file(ufile, **kwargs)

    def _document_upload_files(self, ufile, **kwargs):
        # default folder
        try:
            default_folder_id = int(kwargs.get('folder_id'))
        except ValueError:
            default_folder_id = None

        if not default_folder_id:
            default_folder_id = request.env['document.document'].default_get(['folder_id']).get('folder_id')
        if not default_folder_id:
            default_folder_id = request.env['document.folder'].search([], limit=1, order='sequence ASC').id

        if not default_folder_id:
            return json.dumps({'error': "Can not upload files as there is no default folder or no folder at all."})

        try:
            default_folder_id = int(default_folder_id)
        except ValueError:
            return json.dumps({'error': "Given folder is not valid."})

        # default tags
        candidate_tag_ids = []
        tag_ids_str = kwargs.get('tag_ids', '')
        if tag_ids_str:
            candidate_tag_ids = tag_ids_str.split(',')

        tag_ids = []
        for tag_id in candidate_tag_ids:
            try:
                tag_ids.append(int(tag_id))
            except ValueError:
                return json.dumps({'error': _("Some tag does not exist.")})

        # create documents
        default_folder = request.env['document.folder'].browse(int(default_folder_id))
        result = {'success': _("All files uploaded in %s") % (default_folder.name,)}

        vals_list = []
        files = request.httprequest.files.getlist('ufile')
        for ufile in files:
            try:
                mimetype = ufile.content_type
                datas = base64.encodebytes(ufile.read())
                vals = {
                    'name': ufile.filename,
                    'content_b64': datas,
                    'folder_id': default_folder.id,
                }
                if tag_ids:
                    vals['tag_ids'] = [(6, 0, tag_ids)]
                vals_list.append(vals)
            except Exception as e:
                logger.exception("Fail to upload document %s" % ufile.filename)
                result = {'error': str(e)}
        documents = request.env['document.document'].create(vals_list)
        return json.dumps(result)

    def _document_upload_request_file(self, ufile, **kwargs):
        try:
            document_id = int(kwargs.get('document_id'))
            document = request.env['document.document'].browse(document_id)
        except ValueError:
            return json.dumps({'error': "Incorrect document ID received."})

        if document.document_type != 'request':
            return json.dumps({'error': "The document is not a request."})

        try:
            files = request.httprequest.files.getlist('ufile')
            datas = base64.encodebytes(files[0].read())
            document.set_request_file(datas)
            result = {'success': _("File uploaded as %s") % (document.name,)}
            return json.dumps(result)
        except IndexError:
            return json.dumps({'error': "No file uploaded."})

    # ------------------------------------------------------------------
    # Frontend Page
    # ------------------------------------------------------------------

    @http.route(['/document/share/<int:share_id>/<access_token>'], type='http', website=True, auth='public')
    def page_share_documents(self, share_id=None, access_token=None, **kwargs):
        """ Main HTML page to expose document list to download.

            :param share_id: id of the share link
            :param token: access token of document.share
        """
        share = request.env['document.share'].sudo().browse(share_id)
        can_access, response = self._document_can_access_share(share, access_token)
        if can_access:
            documents = share.get_concerned_documents()[share.id]
            params = {
                'base_url': http.request.env["ir.config_parameter"].sudo().get_param("web.base.url"),
                'share': share,
                'share_access_token': access_token,
                'documents': documents,
                'at_least_binary': 'file' in documents.mapped('document_type'),
            }
            return request.render('document.page_document_share', params)
        return response

    # ------------------------------------------------------------------
    # Image Routes
    # ------------------------------------------------------------------

    @http.route(["/document/owner_avatar/<int:share_id>/<access_token>"], type='http', auth='public')
    def document_owner_avatar(self, access_token=None, share_id=None):
        share = request.env['document.share'].sudo().browse(share_id)
        can_access, response = self._document_can_access_share(share, access_token)
        if can_access:
            # TODO JEM: make a proper response with correct headers
            return base64.b64decode(request.env['res.users'].sudo().browse(share.create_uid.id).image_128)
        return response

    @http.route(["/document/thumbnail/<int:share_id>/<access_token>/<int:document_id>"], type='http', auth='public')
    def document_thumbnail(self, share_id, access_token, document_id):
        share = request.env['document.share'].sudo().browse(share_id)
        can_access, response = self._document_can_access_share(share, access_token)
        if can_access:
            # TODO JEM: make a proper response with correct headers
            thumbnail = request.env['document.document'].sudo().browse(document_id).thumbnail
            if thumbnail:
                return base64.b64decode(thumbnail)
            return request.env['ir.binary']._placeholder()
        return response

    # ------------------------------------------------------------------
    # Documents Routes (Download & Upload)
    # ------------------------------------------------------------------

    @http.route(["/document/download/<int:share_id>/<access_token>/<int:document_id>"], type='http', auth='public')
    def document_download(self, share_id=None, access_token=None, document_id=None):
        share = request.env['document.share'].sudo().browse(share_id)
        can_access, response = self._document_can_access_share(share, access_token)
        if can_access:
            # Inspired from odoo.addons.web.controllers.main.Binary.content_common
            # The idea is to serve the related ir.attachment, as Odoo support it
            # natively, but this required the attachment to have an access token.
            document = request.env['document.document'].sudo().browse(document_id)

            with replace_exceptions(UserError, by=request.not_found()):
                record = request.env['ir.binary']._find_record(xmlid=None, res_model='ir.attachment', res_id=document.attachment_id.id, access_token=document.attachment_id.access_token)
                stream = request.env['ir.binary']._get_stream_from(record, field_name='datas', filename=document.filename, mimetype=document.attachment_id.mimetype)
            send_file_kwargs = {'as_attachment': True}
            send_file_kwargs['immutable'] = True
            send_file_kwargs['max_age'] = http.STATIC_CACHE_LONG

            response = stream.get_response(**send_file_kwargs)
            response.headers['Content-Security-Policy'] = "default-src 'none'"

        return response

    @http.route(["/document/download/all/<int:share_id>/<access_token>"], type='http', auth='public')
    def document_download_all(self, share_id, access_token):
        share = request.env['document.share'].sudo().browse(share_id)
        can_access, response = self._document_can_access_share(share, access_token)
        if can_access:
            return self._document_make_zip(share.name, share.get_concerned_documents()[share.id])
        return response

    @http.route(["/document/upload/<int:share_id>/<access_token>/"], type='http', auth='public', methods=['POST'], csrf=False)
    def document_upload(self, share_id, access_token, **kwargs):
        share = request.env['document.share'].sudo().browse(share_id)
        can_access, response = self._document_can_access_share(share, access_token)
        if can_access:
            document_value_list = []
            for file in request.httprequest.files.getlist('files'):
                document_values = share.get_document_default_values()[share.id]
                data = file.read()
                document_values.update({
                    'name': file.filename,
                    'filename': file.filename,
                    'content_b64': base64.b64encode(data),
                    'description': file.filename,
                })
                document_value_list.append(document_values)

            documents = request.env['document.document'].sudo().create(document_value_list)
            share._postprocess_upload(documents)
            return """<script type='text/javascript'>
                    window.open("/document/share/%s/%s", "_self");
                </script>""" % (share_id, access_token)

        return request.not_found()

    # ------------------------------------------------------------------
    # Utils
    # ------------------------------------------------------------------

    def _document_can_access_share(self, share, token):
        """ Check if the share is valide (exists, is not expired, ....)
            :returns : (True, None) if the access is granted. The response must be build by the
                caller. (False, <http.Response>) with the response explaining the refused access otherwise.
        """
        if share.exists():
            if share.state == 'expired':
                return False, request.render('document.page_document_expired')
            if not consteq(token, share.access_token):
                return request.not_found()
            return True, None
        return False, request.not_found()

    def _document_make_zip(self, name, documents):
        """ returns zip files for the Document Inspector and the portal.
            :param name: the name to give to the zip file
            :param attachments: recorset of ir.attachment to compress
            :return: a HTTP response to download a zip file
        """
        name = name + '.zip'
        stream = io.BytesIO()
        try:
            with zipfile.ZipFile(stream, 'w') as zip_file:
                for document in documents:
                    if document.document_type == 'file':
                        filename = document.filename
                        zip_file.writestr(filename, base64.b64decode(document.content_b64), compress_type=zipfile.ZIP_DEFLATED)
        except zipfile.BadZipfile:
            logger.exception("BadZipfile exception: trying to download document share %s", name)

        content = stream.getvalue()
        headers = [
            ('X-Content-Type-Options', 'nosniff'),
            ('Content-Type', 'zip'),
            ('Content-Disposition', content_disposition(name)),
            ('Content-Length', len(content)),
        ]
        return request.make_response(content, headers)
