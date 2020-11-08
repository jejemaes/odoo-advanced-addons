# -*- coding: utf-8 -*-

import logging

from odoo.models import AbstractModel
from odoo import api

_logger = logging.getLogger(__name__)


class PublisherWarrantyContract(AbstractModel):
    _inherit = "publisher_warranty.contract"

    def update_notification(self, cron_mode=True):
        """ Prevent the ping ! """
        return False
