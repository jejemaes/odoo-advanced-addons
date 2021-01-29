from odoo import api, fields, models


class Company(models.Model):
    _inherit = 'res.company'

    @api.model_create_multi
    def create(self, values):
        company = super(Company, self).create(values)
        company.sudo()._create_default_pos_kitchen_stages()
        return company

    def _create_default_pos_kitchen_stages(self):
        value_list = []
        for company in self:
            value_list.append({
                'name': "New",
                'button_text': "Prepare",
                'sequence': 1,
                'color': 1,
                'is_closed': False,
                'fold': False,
                'company_id': company.id,
            })
            value_list.append({
                'name': "Ongoing",
                'button_text': "Finish",
                'sequence': 2,
                'color': 3,
                'is_closed': False,
                'fold': False,
                'company_id': company.id,
            })
            value_list.append({
                'name': "Finished",
                'button_text': "Done",
                'sequence': 3,
                'color': 4,
                'is_closed': True,
                'fold': True,
                'company_id': company.id,
            })
        self.env['restaurant.kitchen.stage'].create(value_list)

    @api.model
    def generate_kitchen_stage(self):
        company_ids = self.env['restaurant.kitchen.stage'].search([]).mapped('company_id').ids
        self.env['res.company'].search([('id', 'not in', company_ids)])._create_default_pos_kitchen_stages()
