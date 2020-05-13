# -*- coding: utf-8 -*-
from datetime import datetime, date

from odoo import fields
from odoo.addons.sale_rental.tests.common import TestCommonSaleRentalNoChart
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import Form


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
    # Add Rental Lines
    # --------------------------------------------------------------

    def test_add_rental_line_day_without_resources(self):
        form = Form(self.env['rental.add.product'].with_context(active_model='sale.order', active_id=self.sale_order.id, tz='Europe/Brussels'))
        form.sale_order_id = self.sale_order
        form.display_date_from = date(2020, 5, 7)
        form.display_date_to = date(2020, 5, 10)
        form.product_id = self.product_rental_day2
        form.product_qty = 3
        wizard = form.save()

        self.assertEqual(form.datetime_from, datetime(2020, 5, 6, 22, 0))
        self.assertEqual(form.datetime_to, datetime(2020, 5, 10, 22, 0))

        sale_line_ids = wizard.action_add_line()
        sale_line = self.env['sale.order.line'].browse(sale_line_ids[0])

        self.assertTrue(sale_line.is_rental)
        self.assertEqual(sale_line.price_unit, 175)
        self.assertEqual(sale_line.product_uom_qty, 3)
        self.assertEqual(sale_line.qty_delivered, 0)
        self.assertEqual(sale_line.qty_delivered_method, 'manual')
        self.assertEqual(sale_line.rental_start_date, datetime(2020, 5, 6, 22, 0))
        self.assertEqual(sale_line.rental_stop_date, datetime(2020, 5, 10, 22, 0))

        self.assertEqual(len(sale_line.rental_booking_ids), 0)
        self.assertEqual(len(sale_line.resource_ids), 0)

    def test_add_rental_line_day_with_resources(self):
        form = Form(self.env['rental.add.product'].with_context(active_model='sale.order', active_id=self.sale_order.id, tz='Europe/Brussels'))
        form.sale_order_id = self.sale_order
        form.display_date_from = date(2020, 5, 7)
        form.display_date_to = date(2020, 5, 10)
        form.product_id = self.product_rental_day1
        form.resource_ids.add(self.product_rental_day1_resource1)
        form.resource_ids.add(self.product_rental_day1_resource2)
        wizard = form.save()

        self.assertEqual(form.datetime_from, datetime(2020, 5, 6, 22, 0))
        self.assertEqual(form.datetime_to, datetime(2020, 5, 10, 22, 0))

        sale_line_ids = wizard.action_add_line()
        sale_line = self.env['sale.order.line'].browse(sale_line_ids[0])

        self.assertTrue(sale_line.is_rental)
        self.assertEqual(sale_line.price_unit, 175)
        self.assertEqual(sale_line.product_uom_qty, 2)
        self.assertEqual(sale_line.qty_delivered, 0)
        self.assertEqual(sale_line.qty_delivered_method, 'rental')
        self.assertEqual(sale_line.rental_start_date, datetime(2020, 5, 6, 22, 0))
        self.assertEqual(sale_line.rental_stop_date, datetime(2020, 5, 10, 22, 0))

        self.assertEqual(len(sale_line.rental_booking_ids), 2)
        self.assertEqual(sale_line.rental_booking_ids.mapped('resource_id'), self.product_rental_day1_resource1 | self.product_rental_day1_resource2)
        self.assertEqual(sale_line.resource_ids, self.product_rental_day1_resource1 | self.product_rental_day1_resource2)

    def test_add_rental_line_duration_without_resources(self):
        pass

    def test_add_rental_line_duration_with_resources(self):
        pass

    # --------------------------------------------------------------
    # Corner Cases
    # --------------------------------------------------------------

    def test_no_tenure(self):
        """ rental should be free """
        # remove tenures
        self.product_rental_day2.rental_tenure_day_ids.unlink()

        start_dt = datetime(2020, 5, 7, 0, 0, 0)
        stop_dt = datetime(2020, 5, 8, 0, 0, 0)

        # create and confirm the wizard
        wizard = self.env['rental.add.product'].with_context(active_model='sale.order', active_id=self.sale_order.id, tz='Europe/Brussels').create({
            'sale_order_id': self.sale_order.id,
            'datetime_from': start_dt,
            'datetime_to': stop_dt,
            'product_id': self.product_rental_day2.id,
        })
        sale_line_ids = wizard.action_add_line()
        sale_line = self.env['sale.order.line'].browse(sale_line_ids[0])

        self.assertEqual(sale_line.price_unit, 0)
