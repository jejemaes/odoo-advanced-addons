# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import fields
from odoo.addons.sale_rental.tests.common import TestCommonSaleRentalNoChart
from odoo.exceptions import UserError, ValidationError


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
    # Rental cases with different tenure and resource tracked mode
    # --------------------------------------------------------------

    def test_sale_rental_day_without_resources(self):
        product_id = self.product_rental_day2.id
        uom_id = self.product_rental_day2.uom_id.id

        with self.assertRaises(ValidationError):  # rental duration must be greater than one 1 day
            rental_start_date = fields.Datetime.to_string(datetime(2020, 5, 7, 3, 0, 0))
            rental_stop_date = fields.Datetime.to_string(datetime(2020, 5, 7, 14, 0, 0))
            self.sale_order.create_rental_line(product_id, uom_id, 55, rental_start_date, rental_stop_date, quantity=3, additional_description='blablabla')

        start_dt = datetime(2020, 5, 7, 0, 0, 0)
        stop_dt = datetime(2020, 5, 8, 0, 0, 0)
        rental_start_date = fields.Datetime.to_string(start_dt)
        rental_stop_date = fields.Datetime.to_string(stop_dt)
        self.sale_order.create_rental_line(product_id, uom_id, 55, rental_start_date, rental_stop_date, quantity=3, additional_description='blablabla')

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

    def test_sale_rental_day_with_resources(self):
        # create the rental line with "Caravane 1" and "Caravane 2" as resources
        product_id = self.product_rental_day1.id
        uom_id = self.product_rental_day1.uom_id.id
        resource_ids = [self.product_rental_day1_resource1.id, self.product_rental_day1_resource2.id]

        with self.assertRaises(ValidationError):  # rental duration must be greater than one 1 day
            rental_start_date = fields.Datetime.to_string(datetime(2020, 5, 7, 3, 0, 0))
            rental_stop_date = fields.Datetime.to_string(datetime(2020, 5, 7, 14, 0, 0))
            self.sale_order.create_rental_line(product_id, uom_id, 55, rental_start_date, rental_stop_date, resource_ids=resource_ids, additional_description='blablabla')

        start_dt = datetime(2020, 5, 7, 0, 0, 0)
        stop_dt = datetime(2020, 5, 8, 0, 0, 0)
        rental_start_date = fields.Datetime.to_string(start_dt)
        rental_stop_date = fields.Datetime.to_string(stop_dt)
        self.sale_order.create_rental_line(product_id, uom_id, 55, rental_start_date, rental_stop_date, resource_ids=resource_ids, additional_description='blablabla')

        # sale order in draft
        self.assertEqual(self.sale_order.rental_count, 2, "One booking generated even if SO is in draft")
        sale_line = self.sale_order.order_line[-1]  # cache problem, the first failed line is still in the cache
        booking1 = self.sale_order.rental_booking_ids[0]
        booking2 = self.sale_order.rental_booking_ids[1]

        self.assertTrue(sale_line.is_rental, "The sale line is rental")
        self.assertEqual(sale_line.price_unit, 55)
        self.assertTrue("blablabla" in sale_line.name)
        self.assertEqual(sale_line.rental_start_date, start_dt, "Rental start date should be correct")
        self.assertEqual(sale_line.rental_stop_date, stop_dt, "Rental stop date should be correct")
        self.assertEqual(sale_line.qty_delivered_method, "rental", "The qty delivered mode is rental, since product is in use_resource mode")
        self.assertEqual(sale_line.qty_delivered, 0, "The delivered quantity is zero as the bookings are in draft")
        self.assertEqual(sale_line.product_uom_qty, len(resource_ids), "The ordered quantity is the total of resources")
        self.assertEqual(sale_line.resource_ids.ids, resource_ids, "The resources should be linked to the sale line")

        self.assertEqual(set(self.sale_order.rental_booking_ids.mapped('state')), set(['draft']), "All rental bookings are in draft")
        self.assertEqual(booking1.date_from, start_dt)
        self.assertEqual(booking1.date_to, stop_dt)
        self.assertEqual(booking2.date_from, start_dt)
        self.assertEqual(booking2.date_to, stop_dt)

        # sale order confirmed
        self.sale_order.action_confirm()

        self.assertTrue("blablabla" in sale_line.name)
        self.assertEqual(sale_line.rental_start_date, start_dt, "Rental start date should still be correct")
        self.assertEqual(sale_line.rental_stop_date, stop_dt, "Rental stop date should still be correct")
        self.assertEqual(sale_line.qty_delivered_method, "rental", "The qty delivered mode is still rental, since product is in use_resource mode")
        self.assertEqual(sale_line.qty_delivered, 0, "The delivered quantity is still zero as the bookings are in draft")
        self.assertEqual(sale_line.product_uom_qty, len(resource_ids), "The ordered quantity is the total of resources")
        self.assertEqual(sale_line.resource_ids.ids, resource_ids, "The resources should be linked to the sale line")

        self.assertEqual(set(self.sale_order.rental_booking_ids.mapped('state')), set(['reserved']), "All rental bookings should be in reserved state")
        self.assertEqual(booking1.date_from, start_dt)
        self.assertEqual(booking1.date_to, stop_dt)
        self.assertEqual(booking2.date_from, start_dt)
        self.assertEqual(booking2.date_to, stop_dt)

        # pick up one booking
        booking1.action_pick_up()

        self.assertTrue("blablabla" in sale_line.name)
        self.assertEqual(sale_line.rental_start_date, start_dt, "Rental start date should still be correct")
        self.assertEqual(sale_line.rental_stop_date, stop_dt, "Rental stop date should still be correct")
        self.assertEqual(sale_line.qty_delivered_method, "rental", "The qty delivered mode is still rental, since product is in use_resource mode")
        self.assertEqual(sale_line.qty_delivered, 1, "The delivered quantity is one as one of the bookings is picked_up")
        self.assertEqual(sale_line.product_uom_qty, len(resource_ids), "The ordered quantity is the total of resources")
        self.assertEqual(sale_line.resource_ids.ids, resource_ids, "The resources should be linked to the sale line")

        self.assertEqual(booking1.state, 'picked_up', "Rental booking 1 is picked up")
        self.assertEqual(booking2.state, 'reserved', "Rental booking 2 is pstill reserved")
        self.assertEqual(booking1.date_from, start_dt)
        self.assertEqual(booking1.date_to, stop_dt)
        self.assertEqual(booking2.date_from, start_dt)
        self.assertEqual(booking2.date_to, stop_dt)

    def test_sale_rental_duration_without_resources(self):
        pass

    def test_sale_rental_duration_with_resources(self):
        pass

    # --------------------------------------------------------------
    # Corner Cases
    # --------------------------------------------------------------

    def test_sale_cancel(self):
        pass
