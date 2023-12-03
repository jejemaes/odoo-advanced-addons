# -*- coding: utf-8 -*-

from odoo.addons.sale.tests.common import TestSaleCommon


class TestCommonSaleRental(TestSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
            'company_id': False, # shared partner
        })
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')


    @classmethod
    def setup_sale_configuration_for_company(cls, company):
        company_data = super(TestCommonSaleRental, cls).setup_sale_configuration_for_company(company)

        # Resource Calendar (full day)
        company_data['resource_calendar_full_day'] = cls.env['resource.calendar'].sudo().with_company(company).create({
            'name': "All Days 24/7",
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

        # Resources
        company_data['resource_resource1'] = cls.env['resource.resource'].sudo().with_company(company).create({
            'name': 'Material to rent 1',
            'calendar_id': company_data['resource_calendar_full_day'].id,
            'tz': 'Europe/Brussels',
            'active': True,
            'resource_type': 'material',
        })
        company_data['resource_resource2'] = cls.env['resource.resource'].sudo().with_company(company).create({
            'name': 'Material to rent 2',
            'calendar_id': company_data['resource_calendar_full_day'].id,
            'tz': 'Europe/Brussels',
            'active': True,
            'resource_type': 'material',
        })

        # Product Category
        company_data['product_category'] = cls.env['product.category'].sudo().with_company(company).create({
            'name': 'Test Category for Rental Products',
        })

        return company_data
