# -*- coding: utf-8 -*-

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
        user_id = state.get('uid', request.session.uid)
        url_return = state.get('return_url', '/web')
        scopes = state['scopes']  # mandatory parameter

        with registry(dbname).cursor() as cr:
            if kw.get('code'):
                request.env(cr, user_id)['google.api']._auth_exchange_code_for_tokens(kw['code'], scopes)
                return redirect(url_return)
            elif kw.get('error'):
                return redirect("%s%s%s" % (url_return, "?error=", kw['error']))
            else:
                return redirect("%s%s" % (url_return, "?error=Unknown_error"))
