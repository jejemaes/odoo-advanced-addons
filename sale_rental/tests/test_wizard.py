# -*- coding: utf-8 -*-

from datetime import datetime, date

from odoo.addons.sale_rental.tests.common import TestCommonSaleRentalNoChart
from odoo.exceptions import UserError
from odoo.tests.common import Form


class TestSaleRentalWizard(TestCommonSaleRentalNoChart):

    @classmethod
    def setUpClass(cls):
        super(TestSaleRentalWizard, cls).setUpClass()
        cls.setUpRentalProducts()

        cls.rental_booking = cls.env['rental.booking'].create({
            'resource_id': cls.product_rental_day1_resource1.id,
            'date_from': datetime(2020, 5, 7, 3, 0, 0),
            'date_to': datetime(2020, 5, 9, 0, 0, 0),
            'partner_id': cls.partner_a.id,
            'state': 'draft',
        })
        cls.resource_no_product = cls.env['resource.resource'].create({
            'name': 'Nothing',
            'resource_type': 'material',
            'calendar_id': cls.calendar_eur.id,
            'tz': 'Europe/Brussels',
            'product_id': False,
        })

    def test_rental_draft(self):
        """ From a draft rental, create a SO """
        form_wizard = Form(self.env['rental.create.sale.order'].with_context(
            active_model='rental.booking',
            active_id=self.rental_booking.id
        ))
        wizard = form_wizard.save()

        action = wizard.action_create_sale_order()
        sale_order = self.env['sale.order'].browse(action['res_id'])

        self.assertEqual(sale_order.state, 'draft')
        self.assertEqual(len(sale_order.order_line), 1)
        self.assertEqual(sale_order.rental_count, 1)
        self.assertEqual(sale_order.rental_booking_ids, self.rental_booking)

        sale_line = sale_order.order_line[0]
        start_dt = datetime(2020, 5, 7, 3, 0, 0)
        stop_dt = datetime(2020, 5, 9, 0, 0, 0)
        price, pricing_explanation = self.rental_booking.resource_product_id.get_rental_price_and_details(start_dt, stop_dt, sale_order.pricelist_id)

        self.assertEqual(sale_line.rental_start_date, start_dt)
        self.assertEqual(sale_line.rental_stop_date, stop_dt)
        self.assertEqual(sale_line.price_unit, price)
        self.assertEqual(sale_line.rental_pricing_explanation, pricing_explanation)
        self.assertEqual(sale_line.resource_ids, self.rental_booking.resource_id)
        self.assertEqual(sale_line.rental_booking_ids, self.rental_booking)

    def test_rental_reserved(self):
        """ From a reserved rental, create a SO (confirmed) """
        self.rental_booking.action_reserve()

        form_wizard = Form(self.env['rental.create.sale.order'].with_context(
            active_model='rental.booking',
            active_id=self.rental_booking.id
        ))
        wizard = form_wizard.save()

        action = wizard.action_create_sale_order()
        sale_order = self.env['sale.order'].browse(action['res_id'])

        self.assertEqual(sale_order.state, 'sale')  # order is confirmed
        self.assertEqual(len(sale_order.order_line), 1)
        self.assertEqual(sale_order.rental_count, 1)
        self.assertEqual(sale_order.rental_booking_ids, self.rental_booking)

        sale_line = sale_order.order_line[0]
        start_dt = datetime(2020, 5, 7, 3, 0, 0)
        stop_dt = datetime(2020, 5, 9, 0, 0, 0)
        price, pricing_explanation = self.rental_booking.resource_product_id.get_rental_price_and_details(start_dt, stop_dt, sale_order.pricelist_id)

        self.assertEqual(sale_line.rental_start_date, start_dt)
        self.assertEqual(sale_line.rental_stop_date, stop_dt)
        self.assertEqual(sale_line.price_unit, price)
        self.assertEqual(sale_line.rental_pricing_explanation, pricing_explanation)
        self.assertEqual(sale_line.resource_ids, self.rental_booking.resource_id)
        self.assertEqual(sale_line.rental_booking_ids, self.rental_booking)

    def test_rental_no_product(self):
        """ Create a SO from a rental with a resource having no product is prevent. """
        self.rental_booking.write({'resource_id': self.resource_no_product.id})

        with self.assertRaises(UserError):
            form_wizard = Form(self.env['rental.create.sale.order'].with_context(
                active_model='rental.booking',
                active_id=self.rental_booking.id
            ))
            form_wizard.save()
