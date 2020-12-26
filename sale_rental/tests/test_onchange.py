# -*- coding: utf-8 -*-
from datetime import datetime, date

from odoo import fields, tools
from odoo.addons.sale_rental.tests.common import TestCommonSaleRentalNoChart
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import Form


class TestOnchangeFlow(TestCommonSaleRentalNoChart):

    @classmethod
    def setUpClass(cls):
        super(TestOnchangeFlow, cls).setUpClass()
        cls.setUpRentalProducts()

    # --------------------------------------------------------------
    # Sale a rental non tracked product
    # --------------------------------------------------------------

    def test_sale_rental_no_tracked_weekday(self):
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.partner_a
        with so_form.order_line.new() as line:
            line.is_rental = True
            line.product_id = self.product_rental_day2
            line.product_uom_qty = 2
            line.rental_start_date = datetime(2020, 11, 20, 14, 15, 00)
            line.rental_stop_date = datetime(2020, 11, 22, 22, 00, 00)
        sale_order = so_form.save()

        sale_line = sale_order.order_line[0]

        self.assertTrue(sale_line.is_rental)
        self.assertEqual(sale_line.price_unit, 125)
        self.assertEqual(sale_line.product_uom_qty, 2)
        self.assertEqual(sale_line.qty_delivered, 0)
        self.assertEqual(sale_line.qty_delivered_method, 'manual')
        self.assertEqual(sale_line.rental_pricing_explanation, '1 * Friday ($\xa050.00) + 1 * Saturday, Sunday ($\xa075.00)')
        self.assertEqual(len(sale_line.rental_booking_ids), 0)
        self.assertEqual(len(sale_line.resource_ids), 0)

    def test_sale_rental_no_tracked_duration(self):
        pass

    # --------------------------------------------------------------
    # Sale a rental tracked product
    # --------------------------------------------------------------

    def test_sale_rental_use_resource_weekday(self):
        # reource_ids is required as the product use_resources
        with self.assertRaises(ValidationError):
            so_form = Form(self.env['sale.order'])
            so_form.partner_id = self.partner_a
            with so_form.order_line.new() as line:
                line.is_rental = True
                line.product_id = self.product_rental_day1
                line.rental_start_date = datetime(2020, 11, 20, 14, 15, 00)
                line.rental_stop_date = datetime(2020, 11, 22, 22, 00, 00)
            so_form.save()

        start_dt = datetime(2020, 11, 20, 14, 15, 00)
        stop_dt = datetime(2020, 11, 22, 21, 00, 00)

        so_form = Form(self.env['sale.order'], view='sale.view_order_form')
        so_form.partner_id = self.partner_a
        with so_form.order_line.new() as line:
            line.is_rental = True
            line.product_id = self.product_rental_day1
            line.product_uom = self.product_rental_day1.uom_id
            line.rental_start_date = start_dt
            line.rental_stop_date = stop_dt
            line.resource_ids.add(self.product_rental_day1_resource1)
            line.resource_ids.add(self.product_rental_day1_resource2)
        sale_order = so_form.save()

        sale_line = sale_order.order_line[0]
        start_str = tools.format_datetime(self.env, start_dt, tz=self.partner_a.tz, lang_code=self.partner_a.lang)
        end_str = tools.format_datetime(self.env, stop_dt, tz=self.partner_a.tz, lang_code=self.partner_a.lang)
        name = '%s\n%s\nRental from %s to %s' % (self.product_rental_day1.display_name, self.product_rental_day1.description_rental, start_str, end_str)

        self.assertTrue(sale_line.is_rental)
        self.assertEqual(sale_line.name, name)
        self.assertEqual(sale_line.price_unit, 125)
        self.assertEqual(sale_line.product_uom_qty, 2)
        self.assertEqual(sale_line.qty_delivered, 0)
        self.assertEqual(sale_line.qty_delivered_method, 'rental')
        self.assertEqual(sale_line.rental_pricing_explanation, '1 * Friday ($\xa050.00) + 1 * Saturday, Sunday ($\xa075.00)')
        self.assertEqual(len(sale_line.rental_booking_ids), 0)
        self.assertEqual(len(sale_line.resource_ids), 2)

    def test_sale_rental_use_resource_duration(self):
        pass
