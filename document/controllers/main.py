# -*- coding: utf-8 -*-

import base64
import zipfile
import io
import logging

import werkzeug
import werkzeug.exceptions
import werkzeug.routing
import werkzeug.urls
import werkzeug.utils
from werkzeug.exceptions import Forbidden

from ast import literal_eval

from odoo import http, fields, models
from odoo.http import request, content_disposition
from odoo.osv import expression
from odoo.tools import pycompat, consteq
from odoo.addons.web.controllers.main import Binary

logger = logging.getLogger(__name__)


class ShareRoute(http.Controller):

    # ------------------------------------------------------------------
    # Backend Action
    # ------------------------------------------------------------------

    @http.route(['/document/zip_download/<file_ids>'], type='http', auth='user')
    def document_action_backend(self, file_ids, **kwargs):
        zip_name = 'documents-%s' % fields.Date.to_string(fields.Date.today())
        ids_list = [int(x) for x in file_ids.split(',')]
        return self._document_make_zip(zip_name, request.env['document.document'].browse(ids_list).exists())

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
                'at_least_binary': 'binary' in documents.mapped('type'),
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
            return Binary.placeholder()
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
            status, headers, content = request.env['ir.http'].binary_content(
                xmlid=None, model='ir.attachment', id=document.attachment_id.id, field='datas', unique=False, filename=document.filename,
                filename_field='name', download=True, mimetype=document.mimetype, access_token=document.sudo().access_token
            )
            if status != 200:
                return request.env['ir.http']._response_by_status(status, headers, content)
            else:
                content_base64 = base64.b64decode(content)
                headers.append(('Content-Length', len(content_base64)))
                response = request.make_response(content_base64, headers)
            # if access_token:
            #     response.set_cookie('fileToken', access_token)
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
                    'mimetype': file.content_type,
                    'datas': base64.b64encode(data),
                    'description': file.filename,
                    'company_id': share.company_id.id,
                    'active': True,
                })
                document_value_list.append(document_values)

            documents = request.env['document.document'].create(document_value_list)
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
                    if document.type == 'binary':
                        filename = document.filename
                        zip_file.writestr(filename, base64.b64decode(document.datas), compress_type=zipfile.ZIP_DEFLATED)
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
