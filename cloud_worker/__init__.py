# -*- coding: utf-8 -*-

import logging
from odoo import http
from odoo.http import request
from odoo.tools import config

# keep origin method
_base_db_filter = http.db_filter


def db_filter_headers(dbs, httprequest=None):
    # check the header of the request (prior to old system)
    httprequest = httprequest or request.httprequest
    db_header = httprequest.headers.get('X-Odoo-Dbname')
    if db_header and db_header in dbs:
        return [db_header]
    # otherwise, basic behavior
    return _base_db_filter(dbs, httprequest)

# this is only applied if proxy mode is activated and if this module is loaded
if config.get('proxy_mode') and 'cloud_worker' in config.get('server_wide_modules'):
    _logger = logging.getLogger(__name__)
    _logger.info('monkey patching http.db_filter')
    http.db_filter = db_filter_headers
