# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from werkzeug.utils import redirect

from odoo import http, registry
from odoo.http import request


class GoogleAuth(http.Controller):

    @http.route('/google_account/authentication', type='http', auth="none")
    def goole_oauth2_callback(self, **kw):
        """ This route/function is called by Google when user Accept/Refuse the consent of Google """
        state = json.loads(kw['state'])
        dbname = state.get('dbname')
        url_return = state.get('return_url', '/web')
        scopes = state['scopes']  # mandatory parameter

        with registry(dbname).cursor() as cr:
            if kw.get('code'):
                request.env(cr, request.session.uid)['google.api']._auth_exchange_code_for_tokens(kw['code'], scopes)
                return redirect(url_return)
            elif kw.get('error'):
                return redirect("%s%s%s" % (url_return, "?error=", kw['error']))
            else:
                return redirect("%s%s" % (url_return, "?error=Unknown_error"))
