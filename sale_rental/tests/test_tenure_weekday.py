# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import fields
from odoo.addons.sale_rental.tests.common import TestCommonSaleRental
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestSaleRentalTenurePerDay(TestCommonSaleRental):

    @classmethod
    def setUpClass(cls):
        super(TestSaleRentalTenurePerDay, cls).setUpClass()

        # Rental products
        tenure_weekday_values = [
            (5, 0),
            (0, 0, {
                'base_price': 50,
                'weekday_ids': [
                    (6, 0, [cls.env.ref('resource_advanced.resource_day_monday').id,]),
                ]
            }),
            (0, 0, {
                'base_price': 50,
                'weekday_ids': [
                    (6, 0, [cls.env.ref('resource_advanced.resource_day_tuesday').id,]),
                ]
            }),
            (0, 0, {
                'base_price': 50,
                'weekday_ids': [
                    (6, 0, [cls.env.ref('resource_advanced.resource_day_wednesday').id,]),
                ]
            }),
            (0, 0, {
                'base_price': 50,
                'weekday_ids': [
                    (6, 0, [cls.env.ref('resource_advanced.resource_day_thursday').id,]),
                ]
            }),
            (0, 0, {
                'base_price': 50,
                'weekday_ids': [
                    (6, 0, [cls.env.ref('resource_advanced.resource_day_friday').id,]),
                ]
            }),
            (0, 0, {
                'base_price': 50,
                'weekday_ids': [
                    (6, 0, [cls.env.ref('resource_advanced.resource_day_saturday').id,]),
                ]
            }),
            (0, 0, {
                'base_price': 50,
                'weekday_ids': [
                    (6, 0, [cls.env.ref('resource_advanced.resource_day_sunday').id,]),
                ]
            }),
            (0, 0, {
                'base_price': 75,
                'weekday_ids': [
                    (6, 0, [
                        cls.env.ref('resource_advanced.resource_day_saturday').id,
                        cls.env.ref('resource_advanced.resource_day_sunday').id,
                    ]),
                ]
            }),
        ]

        # Rental product, with resource
        cls.product_resource_tracked = cls.env['product.product'].create({
            'name': "Service Rental, with resources",
            'sale_ok': False,
            'list_price': 0,
            'type': 'consu',
            'invoice_policy': 'order',
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id,
            'default_code': 'RENT-SERV1',
            'can_be_rented': True,
            'rental_tracking': 'use_resource',
            'rental_calendar_id': False,
            'rental_tenure_type': 'weekday',
            'rental_tenure_ids': tenure_weekday_values,
            'description_rental': "blablabla",
        })

        cls.company_data['resource_resource1'].sudo().write({'product_id': cls.product_resource_tracked.id})
        cls.company_data['resource_resource2'].sudo().write({'product_id': cls.product_resource_tracked.id})

        # Rental product, no resource
        cls.product_resource_notrack = cls.env['product.product'].create({
            'name': "Service Rental, without resources",
            'sale_ok': False,
            'list_price': 0,
            'type': 'consu',
            'invoice_policy': 'order',
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id,
            'default_code': 'RENT-SERV2',
            'can_be_rented': True,
            'rental_tracking': 'no',
            'rental_calendar_id': cls.company_data['resource_calendar_full_day'].id,
            'rental_tenure_type': 'weekday',
            'rental_tenure_ids': tenure_weekday_values,
            'description_rental': "blablabla",
            'rental_padding_before': 1,
            'rental_padding_after': 2,
        })

        cls.sale_order = cls.env['sale.order'].with_context(mail_notrack=True, mail_create_nolog=True).create({
            'partner_id': cls.partner.id,
        })

    # --------------------------------------------------------------
    # No Resource
    # --------------------------------------------------------------

    def test_no_resource(self):
        product_id = self.product_resource_notrack.id
        uom_id = self.product_resource_notrack.uom_id.id

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
            # 'price_unit': 55, # will be computed
        })

        # sale order in draft
        self.assertEqual(self.sale_order.rental_count, 0, "No booking generated since product does not tracked resources")

        self.assertTrue(sale_line.is_rental, "The sale line is rental")
        self.assertEqual(sale_line.price_unit, 100)
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

    def test_with_resources(self):
        # create the rental line with 2 resources
        product_id = self.product_resource_tracked.id
        resource_ids = [self.company_data['resource_resource1'].id, self.company_data['resource_resource2'].id]

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
            'price_unit': 55, # force price
            'resource_ids': [(6, 0, resource_ids)],
        })

        # sale order in draft
        self.assertEqual(self.sale_order.rental_count, 0, "One booking generated even if SO is in draft")

        self.assertTrue(sale_line.is_rental, "The sale line is rental")
        self.assertEqual(sale_line.price_unit, 55)
        self.assertTrue("blablabla" in sale_line.name)
        self.assertEqual(sale_line.rental_start_date, start_dt, "Rental start date should be correct")
        self.assertEqual(sale_line.rental_stop_date, stop_dt, "Rental stop date should be correct")
        self.assertEqual(sale_line.qty_delivered_method, "rental", "The qty delivered mode is rental, since product is in use_resource mode")
        self.assertEqual(sale_line.qty_delivered, 0, "The delivered quantity is zero as the bookings are in draft")
        self.assertEqual(sale_line.product_uom_qty, len(resource_ids), "The ordered quantity is the total of resources")
        self.assertEqual(sale_line.resource_ids.ids, resource_ids, "The resources should be linked to the sale line")

        # sale order confirmed
        self.sale_order.action_confirm()
        booking1 = self.sale_order.rental_booking_ids[0]
        booking2 = self.sale_order.rental_booking_ids[1]

        self.assertTrue("blablabla" in sale_line.name)
        self.assertEqual(sale_line.rental_start_date, start_dt, "Rental start date should still be correct")
        self.assertEqual(sale_line.rental_stop_date, stop_dt, "Rental stop date should still be correct")
        self.assertEqual(sale_line.qty_delivered_method, "rental", "The qty delivered mode is still rental, since product is in use_resource mode")
        self.assertEqual(sale_line.qty_delivered, 2, "The delivered quantity is still zero as the bookings are in draft")
        self.assertEqual(sale_line.product_uom_qty, len(resource_ids), "The ordered quantity is the total of resources")
        self.assertEqual(sale_line.resource_ids.ids, resource_ids, "The resources should be linked to the sale line")

        self.assertEqual(set(self.sale_order.rental_booking_ids.mapped('state')), set(['confirmed']), "All rental bookings should be in confirmed state")
        self.assertEqual(booking1.date_from, start_dt)
        self.assertEqual(booking1.date_to, stop_dt)
        self.assertEqual(booking2.date_from, start_dt)
        self.assertEqual(booking2.date_to, stop_dt)

        # mark a booking as done
        booking1.action_done()

        self.assertTrue("blablabla" in sale_line.name)
        self.assertEqual(sale_line.rental_start_date, start_dt, "Rental start date should still be correct")
        self.assertEqual(sale_line.rental_stop_date, stop_dt, "Rental stop date should still be correct")
        self.assertEqual(sale_line.qty_delivered_method, "rental", "The qty delivered mode is still rental, since product is in use_resource mode")
        self.assertEqual(sale_line.qty_delivered, 2, "The delivered quantity is still 2 as delivered qty only count confirmed and done bookings")
        self.assertEqual(sale_line.product_uom_qty, len(resource_ids), "The ordered quantity is the total of resources")
        self.assertEqual(sale_line.resource_ids.ids, resource_ids, "The resources should be linked to the sale line")

        self.assertEqual(booking1.state, 'done', "Rental booking 1 is done")
        self.assertEqual(booking2.state, 'confirmed', "Rental booking 2 is pstill reserved")
        self.assertEqual(booking1.date_from, start_dt)
        self.assertEqual(booking1.date_to, stop_dt)
        self.assertEqual(booking2.date_from, start_dt)
        self.assertEqual(booking2.date_to, stop_dt)

    def test_with_resources_cancel_sale_order(self):
        resource_ids = [self.company_data['resource_resource1'].id, self.company_data['resource_resource2'].id]

        start_dt = datetime(2020, 5, 7, 0, 0, 0)
        stop_dt = datetime(2020, 5, 9, 0, 23, 0)
        rental_start_date = fields.Datetime.to_string(start_dt)
        rental_stop_date = fields.Datetime.to_string(stop_dt)

        sale_line = self.env['sale.order.line'].create({
            'order_id': self.sale_order.id,
            'is_rental': True,
            'product_id': self.product_resource_tracked.id,
            'rental_start_date': rental_start_date,
            'rental_stop_date': rental_stop_date,
            'resource_ids': [(6, 0, resource_ids)],
        })

        # sale order confirmed
        self.sale_order.action_confirm()
        booking1 = self.sale_order.rental_booking_ids[0]
        booking2 = self.sale_order.rental_booking_ids[1]

        # cancel SO
        self.sale_order.action_cancel()
        self.assertTrue("blablabla" in sale_line.name)
        self.assertEqual(sale_line.price_unit, 150)
        self.assertEqual(sale_line.rental_start_date, start_dt, "Rental start date should still be correct")
        self.assertEqual(sale_line.rental_stop_date, stop_dt, "Rental stop date should still be correct")
        self.assertEqual(sale_line.qty_delivered_method, "rental", "The qty delivered mode is still rental, since product is in use_resource mode")
        self.assertEqual(sale_line.qty_delivered, 0, "The delivered quantity is still 2 as delivered qty only count confirmed and done bookings")
        self.assertEqual(sale_line.product_uom_qty, len(resource_ids), "The ordered quantity is the total of resources")
        self.assertEqual(sale_line.resource_ids.ids, resource_ids, "The resources should be linked to the sale line")

        self.assertEqual(booking1.state, 'cancel', "Rental booking 1 is now cancel too")
        self.assertEqual(booking2.state, 'cancel', "Rental booking 2 is now cancel too")
