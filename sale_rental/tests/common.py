# -*- coding: utf-8 -*-

from odoo.addons.sale.tests.test_sale_common import TestCommonSaleNoChart


class TestCommonSaleRentalNoChart(TestCommonSaleNoChart):

    @classmethod
    def setUpRentalProducts(cls):
        """ Create Rental product with related resources """
        # Account
        cls.account_sale = cls.env['account.account'].create({
            'code': 'SERV-2020',
            'name': 'Product Sales - (test)',
            'reconcile': True,
            'user_type_id': cls.env.ref('account.data_account_type_revenue').id,
        })

        # Create Resources, rentable but not tuesday
        cls.calendar_eur = cls.env['resource.calendar'].create({
            'name': "5 days week",
            'tz': 'Europe/Brussels',
            'attendance_mode': 'full_day',
            'attendance_ids': [
                (0, 0, {'dayofweek': '0', 'is_working_day': True}),
                (0, 0, {'dayofweek': '1', 'is_working_day': False}),
                (0, 0, {'dayofweek': '2', 'is_working_day': True}),
                (0, 0, {'dayofweek': '3', 'is_working_day': True}),
                (0, 0, {'dayofweek': '4', 'is_working_day': True}),
                (0, 0, {'dayofweek': '5', 'is_working_day': True}),
                (0, 0, {'dayofweek': '6', 'is_working_day': True}),
            ],
        })

        # Create service products
        uom_unit = cls.env.ref('uom.product_uom_unit')

        cls.product_rental_day1 = cls.env['product.product'].create({
            'name': "Service Rental, with resources",
            'sale_ok': False,
            'list_price': 0,
            'type': 'service',
            'invoice_policy': 'order',
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
            'default_code': 'RENT-SERV1',
            'can_be_rented': True,
            'rental_tracking': 'use_resource',
            'rental_calendar_id': cls.calendar_eur.id,
            'rental_tenure_type': 'day',
            'rental_tenure_day_ids': [
                (5, 0),
                (0, 0, {'monday': True, 'rent_price': 50}),
                (0, 0, {'wednesday': True, 'rent_price': 50}),
                (0, 0, {'thursday': True, 'rent_price': 50}),
                (0, 0, {'friday': True, 'rent_price': 50}),
                (0, 0, {'saturday': True, 'rent_price': 50}),
                (0, 0, {'sunday': True, 'rent_price': 50}),
                (0, 0, {'saturday': True, 'sunday': True, 'rent_price': 75}),
            ],
            'property_account_income_id': cls.account_sale.id,
        })
        cls.product_rental_day2 = cls.env['product.product'].create({
            'name': "Service Rental, without resources",
            'sale_ok': False,
            'list_price': 0,
            'type': 'service',
            'invoice_policy': 'order',
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
            'default_code': 'RENT-SERV2',
            'can_be_rented': True,
            'rental_tracking': 'no',
            'rental_calendar_id': cls.calendar_eur.id,
            'rental_tenure_type': 'day',
            'rental_tenure_day_ids': [
                (5, 0),
                (0, 0, {'monday': True, 'rent_price': 50}),
                (0, 0, {'wednesday': True, 'rent_price': 50}),
                (0, 0, {'thursday': True, 'rent_price': 50}),
                (0, 0, {'friday': True, 'rent_price': 50}),
                (0, 0, {'saturday': True, 'rent_price': 50}),
                (0, 0, {'sunday': True, 'rent_price': 50}),
                (0, 0, {'saturday': True, 'sunday': True, 'rent_price': 75}),
            ],
            'rental_padding_before': 1,
            'rental_padding_after': 2,
            'property_account_income_id': cls.account_sale.id,
        })

        cls.product_rental_day1_resource1 = cls.env['resource.resource'].create({
            'name': 'Caravane 1',
            'calendar_id': cls.calendar_eur.id,
            'tz': 'Europe/Brussels',
            'product_id': cls.product_rental_day1.id,
        })
        cls.product_rental_day1_resource2 = cls.env['resource.resource'].create({
            'name': 'Caravane 2',
            'calendar_id': cls.calendar_eur.id,
            'tz': 'Europe/Brussels',
            'product_id': cls.product_rental_day1.id,
        })
