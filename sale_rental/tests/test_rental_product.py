# -*- coding: utf-8 -*-
from datetime import datetime
from psycopg2 import IntegrityError

from odoo import fields
from odoo.addons.sale_rental.tests.common import TestCommonSaleRental
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestSaleService(TestCommonSaleRental):

    @classmethod
    def setUpClass(cls):
        super(TestSaleService, cls).setUpClass()

        cls.public_pricelist = cls.company_data['default_pricelist']
        cls.ProductModel = cls.env['product.product'].with_company(cls.company_data['company'])

        cls.rental_start_dt = datetime(2020, 5, 7, 0, 0, 0)
        cls.rental_stop_dt = datetime(2020, 5, 8, 0, 0, 0)

        cls.rental_context = {
            'rental_start_dt': fields.Datetime.to_string(cls.rental_start_dt),
            'rental_stop_dt': fields.Datetime.to_string(cls.rental_stop_dt),
        }

    # --------------------------------------------------------------
    # Product Creation
    # --------------------------------------------------------------

    def test_create_consumable(self):
        # non rentable services
        product = self.ProductModel.create({
            'name': "Can create a service non-rentable without tracking",
            'sale_ok': False,
            'list_price': 0,
            'type': 'consu',
            'invoice_policy': 'order',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
            'default_code': 'RENT-CONSU',
            'can_be_rented': False,
            'rental_tracking': False,
            'rental_calendar_id': False,
            'rental_tenure_type': False,
            'rental_tenure_ids': False,
            'description_rental': False,
        })
        with mute_logger('odoo.sql_db'):
            with self.assertRaises(IntegrityError):
                with self.cr.savepoint():
                    product = self.ProductModel.create({
                        'name': "Can not create a service non-rentable without tracking",
                        'sale_ok': False,
                        'list_price': 0,
                        'type': 'consu',
                        'invoice_policy': 'order',
                        'uom_id': self.uom_unit.id,
                        'uom_po_id': self.uom_unit.id,
                        'default_code': 'RENT-CONSU',
                        'can_be_rented': True,
                        'rental_tracking': False,
                        'rental_calendar_id': self.company_data['resource_calendar_full_day'].id,
                        'rental_tenure_type': 'duration',
                        'rental_tenure_ids': False,
                        'description_rental': False,
                    })

    def test_create_product_no_tenure(self):
        """ It is allowed to create rental product without tenure price. This means the rent is free. """
        product = self.ProductModel.create({
            'name': "Service Rental without tenures",
            'sale_ok': False,
            'list_price': 0,
            'type': 'consu',
            'invoice_policy': 'order',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
            'default_code': 'RENT-SERV1',
            'can_be_rented': True,
            'rental_tracking': 'use_resource',
            'rental_calendar_id': False,
            'rental_tenure_type': 'weekday',
            'rental_tenure_ids': False,
            'description_rental': "blablabla",
        })

        product = product.with_context(**self.rental_context)

        pricing_explanation = product.get_rental_pricing_explanation(self.rental_start_dt, self.rental_stop_dt)[product.id]

        self.assertEqual(product.rental_price, 0.0)
        self.assertEqual(pricing_explanation, 'Free')

    def test_create_product_duplicate_tenure_weekday(self):
        """ It is actually allowed to create multiplte time the same weekday tenure: no check is done. The sequence number will
            detemrine which one will be uesd: the first one.
        """
        product_rental = self.ProductModel.create({
            'name': "Service Rental without weekday double tenure",
            'sale_ok': False,
            'list_price': 0,
            'type': 'service',
            'invoice_policy': 'order',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
            'default_code': 'RENT-SERV1',
            'can_be_rented': True,
            'rental_tracking': 'no',
            'rental_calendar_id': self.company_data['resource_calendar_full_day'].id,
            'rental_tenure_type': 'weekday',
            'rental_tenure_ids': [
                (5, 0),
                (0, 0, {
                    'base_price': 50,
                    'weekday_ids': [
                        (6, 0, [
                            self.env.ref('resource_advanced.resource_day_monday').id,
                        ]),
                    ]
                }),
                (0, 0, {
                    'base_price': 50,
                    'weekday_ids': [
                        (6, 0, [
                            self.env.ref('resource_advanced.resource_day_monday').id,
                        ]),
                    ]
                }),
            ],
            'description_rental': "blablabla",
        })

    def test_create_product_duplicate_tenure_duration(self):
        """ Create 2 identical duration tenure is forbidden (SQL constraint) """
        with mute_logger('odoo.sql_db'):
            with self.assertRaises(IntegrityError):
                with self.cr.savepoint():
                    self.ProductModel.create({
                        'name': "Service Rental without duration double tenure",
                        'sale_ok': False,
                        'list_price': 0,
                        'type': 'service',
                        'invoice_policy': 'order',
                        'uom_id': self.uom_unit.id,
                        'uom_po_id': self.uom_unit.id,
                        'default_code': 'RENT-SERV1',
                        'can_be_rented': True,
                        'rental_tracking': 'no',
                        'rental_calendar_id': False,
                        'rental_tenure_type': 'duration',
                        'rental_tenure_ids': [
                            (5, 0),
                            (0, 0, {
                                'base_price': 50,
                                'duration_value': 2,
                                'duration_uom': 'week',
                            }),
                            (0, 0, {
                                'base_price': 50,
                                'duration_value': 2,
                                'duration_uom': 'week',
                            }),
                        ],
                        'description_rental': "blablabla",
                    })

    # --------------------------------------------------------------
    # Tenure Creation
    # --------------------------------------------------------------

    def test_create_weekday_tenure_consecutive_days(self):
        product_rental = self.ProductModel.create({
            'name': "Rental product, test consecutive tenure days",
            'sale_ok': False,
            'list_price': 0,
            'type': 'service',
            'invoice_policy': 'order',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
            'default_code': 'RENT-SERV1',
            'can_be_rented': True,
            'rental_tracking': 'no',
            'rental_calendar_id': self.company_data['resource_calendar_full_day'].id,
            'rental_tenure_type': 'weekday',
            'rental_tenure_ids': [
                (5, 0),
                (0, 0, {
                    'base_price': 50,
                    'weekday_ids': [
                        (6, 0, [
                            self.env.ref('resource_advanced.resource_day_monday').id,
                        ]),
                    ]
                }),
            ],
            'description_rental': "blablabla",
        })

        # sunday, monday and tuesday are consecutive
        product_rental.write({
            'rental_tenure_ids': [
                (0, 0, {
                    'base_price': 50,
                    'weekday_ids': [
                        (6, 0, [
                            self.env.ref('resource_advanced.resource_day_sunday').id,
                            self.env.ref('resource_advanced.resource_day_monday').id,
                            self.env.ref('resource_advanced.resource_day_tuesday').id,
                        ]),
                    ]
                })
            ]
        })

        self.assertEqual(len(product_rental.rental_tenure_ids), 2, "Product has 2 weekday tenures")

        # monday and friday are not consecutive
        # /!\ this will add a 3rd tenures (even if raised) in the cache, so checking the len(product_rental.rental_tenure_ids) is problematic
        with self.assertRaises(ValidationError):
            product_rental.write({
                'rental_tenure_ids': [
                    (0, 0, {
                        'base_price': 50,
                        'weekday_ids': [
                            (6, 0, [
                                self.env.ref('resource_advanced.resource_day_monday').id,
                                self.env.ref('resource_advanced.resource_day_friday').id,
                            ]),
                        ]
                    })
                ]
            })
