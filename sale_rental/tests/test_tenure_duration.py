# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import fields
from odoo.addons.sale_rental.tests.common import TestCommonSaleRentalNoChart
from odoo.exceptions import UserError, ValidationError

from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestSaleService(TestCommonSaleRentalNoChart):

    @classmethod
    def setUpClass(cls):
        super(TestSaleService, cls).setUpClass()
        cls.setUpRentalProducts()

        cls.sale_order = cls.env['sale.order'].with_context(mail_notrack=True, mail_create_nolog=True).create({
            'partner_id': cls.partner_customer_usd.id,
            'partner_invoice_id': cls.partner_customer_usd.id,
            'partner_shipping_id': cls.partner_customer_usd.id,
        })

    # --------------------------------------------------------------
    # No Resource
    # --------------------------------------------------------------

    def test_no_resources_price_any_duration(self):
        product_id = self.product_rental_day2.id
        uom_id = self.product_rental_day2.uom_id.id

        start_dt = datetime(2020, 5, 7, 0, 0, 0)
        stop_dt = datetime(2020, 5, 8, 0, 0, 0)
        rental_start_date = fields.Datetime.to_string(start_dt)
        rental_stop_date = fields.Datetime.to_string(stop_dt)

        sale_line = self.env['sale.order.line'].create({
            'order_id': self.sale_order.id,
            'is_rental': True,
            'product_id': product_id,
            'rental_start_date': rental_start_date,
            'rental_stop_date': rental_stop_date,
            'product_uom_qty': 3,
            'product_uom': uom_id,
            'price_unit': 55,
        })

        # sale order in draft
        self.assertEqual(self.sale_order.rental_count, 0, "No booking generated since product does not tracked resources")
        sale_line = self.sale_order.order_line[-1]  # cache problem, the first failed line is still in the cache

        self.assertTrue(sale_line.is_rental, "The sale line is rental")
        self.assertEqual(sale_line.price_unit, 55)
        self.assertTrue("blablabla" in sale_line.name)
        self.assertEqual(sale_line.rental_start_date, start_dt, "Rental start date should be correct")
        self.assertEqual(sale_line.rental_stop_date, stop_dt, "Rental stop date should be correct")
        self.assertEqual(sale_line.qty_delivered_method, "manual", "The qty delivered mode is rental, since product is not in use_resource mode")
        self.assertEqual(sale_line.qty_delivered, 0, "The delivered quantity is zero ")
        self.assertEqual(sale_line.product_uom_qty, 3, "The ordered quantity is the quantity set")
        self.assertFalse(sale_line.resource_ids, "No resources should be linked to the sale line")

        # sale order confirmed
        self.sale_order.action_confirm()

        self.assertTrue("blablabla" in sale_line.name)
        self.assertEqual(sale_line.rental_start_date, start_dt, "Rental start date should still be correct")
        self.assertEqual(sale_line.rental_stop_date, stop_dt, "Rental stop date should still be correct")
        self.assertEqual(sale_line.qty_delivered_method, "manual", "The qty delivered mode is still rental, since product is in use_resource mode")
        self.assertEqual(sale_line.qty_delivered, 0, "The delivered quantity is still zero as the bookings are in draft")
        self.assertEqual(sale_line.product_uom_qty, 3, "The ordered quantity is the total of resources")
        self.assertFalse(sale_line.resource_ids, "No resources should be linked to the sale line")

    # --------------------------------------------------------------
    # With Resources
    # --------------------------------------------------------------

    def test_sale_rental_duration_without_resources(self):
        pass
