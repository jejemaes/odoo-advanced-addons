# -*- coding: utf-8 -*-

import logging
import os

from lxml import etree

from odoo.loglevels import ustr
from odoo.tools import misc, view_validation

_logger = logging.getLogger(__name__)

_gantt_view_validator = None


@view_validation.validate('map')
def schema_gantt_view(arch, **kwargs):
    global _gantt_view_validator

    if _gantt_view_validator is None:
        with misc.file_open(os.path.join('web_gantt', 'views', 'web_gantt.rng')) as f:
            _gantt_view_validator = etree.RelaxNG(etree.parse(f))

    if _gantt_view_validator.validate(arch):
        return True

    for error in _gantt_view_validator.error_log:
        _logger.error(ustr(error))
    return False
