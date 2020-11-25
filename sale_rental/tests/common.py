# -*- coding: utf-8 -*-

from odoo.addons.sale.tests.common import TestSaleCommon


class TestCommonSaleRentalNoChart(TestSaleCommon):

    @classmethod
    def setUpRentalData(cls):
        # link partner
        cls.partner_customer_usd = cls.partner_a

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
            'working_day_ids': [
                (6, 0, [
                    cls.env.ref('resource_advanced.resource_day_monday').id,
                    cls.env.ref('resource_advanced.resource_day_tuesday').id,
                    cls.env.ref('resource_advanced.resource_day_wednesday').id,
                    cls.env.ref('resource_advanced.resource_day_thursday').id,
                    cls.env.ref('resource_advanced.resource_day_friday').id,
                    cls.env.ref('resource_advanced.resource_day_saturday').id,
                    cls.env.ref('resource_advanced.resource_day_sunday').id,
                ]),
            ]
        })

        cls.uom_unit = cls.env.ref('uom.product_uom_unit')

    @classmethod
    def setUpRentalProducts(cls):
        """ Create Rental product with related resources """
        cls.setUpRentalData()

        # tenure values (weekday)
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
        cls.product_rental_day1 = cls.env['product.product'].create({
            'name': "Service Rental, with resources",
            'sale_ok': False,
            'list_price': 0,
            'type': 'service',
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

        # Rental product, no resource
        cls.product_rental_day2 = cls.env['product.product'].create({
            'name': "Service Rental, without resources",
            'sale_ok': False,
            'list_price': 0,
            'type': 'service',
            'invoice_policy': 'order',
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id,
            'default_code': 'RENT-SERV2',
            'can_be_rented': True,
            'rental_tracking': 'no',
            'rental_calendar_id': cls.calendar_eur.id,
            'rental_tenure_type': 'weekday',
            'rental_tenure_ids': tenure_weekday_values,
            'description_rental': "blablabla",
            'rental_padding_before': 1,
            'rental_padding_after': 2,
            'property_account_income_id': cls.account_sale.id,
        })
