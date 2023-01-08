# -*- coding: utf-8 -*-

from datetime import date, datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class RentalBooking(models.Model):
    _name = 'rental.booking'
    _rec_name = 'code'
    _description = 'Rental Reservation'
    _order = 'date_from desc, id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def _default_date_from(self):
        return fields.Datetime.now()

    @api.model
    def _default_date_to(self):
        return self._default_date_from() + timedelta(days=1)

    @api.model
    def _default_agreement_id(self):
        return self.env.user.company_id.rental_agreement_id

    def _group_expand_states(self, states, domain, order):
        return [key for key, val in type(self).state.selection]

    name = fields.Char('Name')
    company_id = fields.Many2one('res.company', string="Company", readonly=True, default=lambda self: self.env.company)

    resource_id = fields.Many2one('resource.resource', 'Resource')
    resource_color = fields.Integer(related='resource_id.color', readonly=True)

    date_from = fields.Datetime(default=_default_date_from, tracking=True, states={'confirmed': [('readonly', False)], 'done': [('readonly', True)]})
    date_to = fields.Datetime(default=_default_date_to, tracking=True, states={'confirmed': [('readonly', False)], 'done': [('readonly', True)]})

    code = fields.Char('Reference', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, copy=True, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", tracking=True)
    partner_shipping_id = fields.Many2one('res.partner', string='Delivery Address', copy=True, domain="[('commercial_partner_id', '=', partner_id), '|', ('company_id', '=', False), ('company_id', '=', company_id)]", help="Delivery address for current booking.")
    user_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self.env.user, index=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Request'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancel', 'Cancel'),
    ], string='Status', default='draft', required=True, copy=False, tracking=True, group_expand='_group_expand_states')
    state_color = fields.Integer("Color State", compute='_compute_state_color')
    overlap_count = fields.Integer("Number of rental overlapping", compute='_compute_overlap_count')

    note = fields.Text('Internal Notes', copy=False)
    agreement_id = fields.Many2one('rental.agreement', string="Agreement", default=_default_agreement_id, copy=False)

    @api.depends('state', 'overlap_count')
    def _compute_state_color(self):
        color_map = {
            'draft': 8, # grey
            'confirmed': 4, # blue
            'done': 10,  # green
            'cancel': 8, # grey
        }
        for rental in self:
            if rental.overlap_count:
                rental.state_color = 1 # red
            else:
                rental.state_color = color_map.get(rental.state, 1)  # red for no known state

    @api.depends('date_from', 'date_to', 'resource_id')
    def _compute_overlap_count(self):
        overlap_ids_map = dict.fromkeys(self.ids, 0)
        if self.ids:
            query = """
                SELECT t.time_id AS time_id, COUNT(t.time_overlap_id) AS overlap_count
                FROM (
                    SELECT R1.id AS time_id, R2.id AS time_overlap_id
                    FROM rental_booking R1
                        INNER JOIN rental_booking R2 ON (R1.date_to > R2.date_from AND R1.date_from < R2.date_to AND R1.id != R2.id)
                    WHERE R1.resource_id = R2.resource_id
                        AND R1.id IN %s
                ) AS t
                GROUP BY t.time_id
            """
            self.env.cr.execute(query, (tuple(self.ids),))
            data = self.env.cr.dictfetchall()
            overlap_ids_map = {item['time_id']: item['overlap_count'] for item in data}

        for shift in self:
            shift.overlap_count = overlap_ids_map.get(shift.id, 0)

    @api.onchange('resource_id')
    def onchange_resource(self):
        if self.resource_id:
            self.calendar_id = self.resource_id.calendar_id

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            addr = self.partner_id.address_get(['delivery'])
            self.partner_shipping_id = addr['delivery']

    @api.onchange('resource_id')
    def _onchange_resource_id(self):
        if self.resource_id:
            self.user_id = self.resource_id.user_id

    # ---------------------------------------------------------
    # CRUD
    # ---------------------------------------------------------

    def name_get(self):
        result = []
        for rental in self:
            name = _('%s / %s') % (rental.code, rental.name or '')
            result.append((rental.id, name))
        return result

    @api.model_create_multi
    def create(self, value_list):
        for values in value_list:
            # generate the code wit ir.sequence
            if 'code' not in values and not values.get('code'):
                if 'company_id' in values:
                    values['code'] = self.env['ir.sequence'].with_context(force_company=values['company_id']).next_by_code('rental.booking') or _('New')
                else:
                    values['code'] = self.env['ir.sequence'].next_by_code('rental.booking') or _('New')
        return super(RentalBooking, self).create(value_list)

    def unlink(self):
        if any(rental.state not in ['draft', 'cancel'] for rental in self):
            raise UserError(_("Only draft or cancelled bookings can be removed."))

        return super(RentalBooking, self).unlink()

    # ---------------------------------------------------------
    # Actions
    # ---------------------------------------------------------

    def action_confirm(self):
        self._create_resource_time()
        self.write({'state': 'confirmed'})

    def action_done(self):
        if any(booking.state in ['draft', 'cancel'] for booking in self):
            raise ValidationError(_("You can only mark as done confirmed bookings."))
        self.write({'state': 'done'})

    def action_cancel(self):
        if any(booking.state in ['done'] for booking in self):
            raise ValidationError(_("You can not cancel done booking."))
        self._remove_resource_time()
        self.write({'state': 'cancel'})

    def action_reset(self):
        if any(booking.state in ['done'] for booking in self):
            raise ValidationError(_("You can only reset already done bookings."))
        self._remove_resource_time()
        self.write({'state': 'draft'})

    def action_view_overlap(self):
        overlap_ids = set(self.env['rental.booking'].search([('date_to', '>', self.date_from), ('date_from', '<=', self.date_to), ('resource_id', '=', self.resource_id.id)]).ids)
        action = self.env.ref('rental.rental_booking_action_rental').read()[0]
        action['domain'] = [('id', 'in', list(overlap_ids))]
        action['name'] = _('Overlap(s) of %s') % (self.name,)
        action['context'] = {}
        return action

    # ---------------------------------------------------------
    # Business
    # ---------------------------------------------------------

    def _create_resource_time(self):
        values_list = []
        for booking in self:
            values_list.append(booking._get_resource_time_value())
        return self.env['resource.calendar.leaves'].sudo().create(values_list)

    def _get_resource_time_value(self):
        return {
            'name': self.name,
            'resource_id': self.resource_id.id,
            'calendar_id': self.resource_id.calendar_id.id,  # required
            'date_from': self.date_from,
            'date_to': self.date_to,
            'time_type': 'rental',
            'company_id': self.company_id.id,
            'rental_booking_id': self.id,
        }

    def _remove_resource_time(self):
        return self.env['resource.calendar.leaves'].sudo().search([('rental_booking_id', 'in', self.ids)]).unlink()


class RentalAgreement(models.Model):
    _name = 'rental.agreement'
    _description = "Rental Agreement"
    _order = 'create_date DESC'

    name = fields.Char("Name", required=True)
    company_id = fields.Many2one('res.company', "Company", default=lambda self: self.env.company)
    content = fields.Html("Content")

