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
    _inherits = {'resource.calendar.leaves': 'resource_time_id'}

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

    resource_time_id = fields.Many2one('resource.calendar.leaves', string="Time Entry", required=True, domain=[('time_type', '=', 'rental')], auto_join=True, ondelete='cascade')
    time_type = fields.Selection(related='resource_time_id.time_type', inherited=True, default='rental')
    resource_id = fields.Many2one(related='resource_time_id.resource_id', inherited=True, tracking=True, domain=[('resource_type', '=', 'material')], states={'reserved': [('readonly', True)], 'picked_up': [('readonly', True)], 'returned': [('readonly', True)], 'done': [('readonly', True)]}, string="Equipment", required=True, readonly=False)
    resource_color = fields.Integer(related='resource_time_id.resource_id.color', readonly=True)

    date_from = fields.Datetime(default=_default_date_from, inherited=True, related='resource_time_id.date_from', tracking=True, states={'reserved': [('readonly', False)], 'picked_up': [('readonly', True)], 'returned': [('readonly', True)], 'done': [('readonly', True)]}, readonly=False)
    date_to = fields.Datetime(default=_default_date_to, inherited=True, related='resource_time_id.date_to', tracking=True, states={'reserved': [('readonly', False)], 'picked_up': [('readonly', True)], 'returned': [('readonly', True)], 'done': [('readonly', True)]}, readonly=False)

    code = fields.Char('Reference', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, copy=False, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", tracking=True)
    partner_shipping_id = fields.Many2one('res.partner', string='Delivery Address', copy=False, domain="[('commercial_partner_id', '=', partner_id), '|', ('company_id', '=', False), ('company_id', '=', company_id)]", help="Delivery address for current booking.")
    user_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self.env.user, index=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Request'),
        ('reserved', 'Reserved'),
        ('picked_up', 'Picked Up'),
        ('returned', 'Returned'),
        ('done', 'Done'),
        ('cancel', 'Cancel'),
    ], string='Status', default='draft', required=True, copy=False, tracking=True, group_expand='_group_expand_states')
    state_color = fields.Integer("Color State", compute='_compute_state_color')
    overlap_count = fields.Integer("Number of rental overlapping", compute='_compute_overlap_count')

    note = fields.Text('Internal Notes', copy=False)
    agreement_id = fields.Many2one('rental.agreement', string="Agreement", default=_default_agreement_id, copy=False)

    _sql_constraints = [
        ('resource_time_unique', 'UNIQUE(resource_time_id)', "Time Entry can only be linked to one Rental."),
    ]

    @api.depends('state', 'overlap_count')
    def _compute_state_color(self):
        color_map = {
            'draft': 8, # grey
            'reserved': 4, # blue
            'picked_up': 3, # yellow
            'returned': 10,  # green
            'done': 10,  # green
            'cancel': 8, # grey
        }
        for rental in self:
            if rental.overlap_count:
                rental.state_color = 1 # red
            else:
                rental.state_color = color_map.get(rental.state, 1)  # red for no known state

    @api.depends('resource_time_id.date_from', 'resource_time_id.date_to')
    def _compute_overlap_count(self):
        overlap_ids_map = self.mapped('resource_time_id')._get_overlap_data(['rental'])
        for shift in self:
            shift.overlap_count = len(overlap_ids_map.get(shift.resource_time_id.id, []))

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
        resource_ids = [val['resource_id'] for val in value_list if val.get('resource_id')]
        calendar_resource_map = {res.id: res.calendar_id.id for res in self.env['resource.resource'].browse(resource_ids)}

        for values in value_list:
            # force type
            values['time_type'] = 'rental'
            # deduce calendar
            if values.get('resource_id') and values['resource_id'] in calendar_resource_map:
                values['calendar_id'] = calendar_resource_map[values['resource_id']]
            # generate the code wit ir.sequence
            if 'code' not in values and not values.get('code'):
                if 'company_id' in values:
                    values['code'] = self.env['ir.sequence'].with_context(force_company=values['company_id']).next_by_code('rental.booking') or _('New')
                else:
                    values['code'] = self.env['ir.sequence'].next_by_code('rental.booking') or _('New')
        res = super(RentalBooking, self).create(value_list)
        return res

    def unlink(self):
        if any(rental.state not in ['draft', 'cancel'] for rental in self):
            raise UserError(_("Only draft or cancelled bookings can be removed."))

        resource_times = self.mapped('resource_time_id')
        result = super(RentalBooking, self).unlink()
        resource_times.sudo().unlink()
        return result

    # ---------------------------------------------------------
    # Actions
    # ---------------------------------------------------------

    def action_reserve(self):
        self.write({'state': 'reserved'})

    def action_pick_up(self):
        self.write({'state': 'picked_up'})

    def action_return(self):
        self.write({'state': 'returned'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        if any(booking.state in ['picked_up'] for booking in self):
            raise ValidationError(_("You can not cancel a picked up booking. It needs to be returned first."))
        self.write({'state': 'cancel'})

    def action_reset(self):
        self.write({'state': 'draft'})

    def action_view_overlap(self):
        overlap_ids = set(self.env['rental.booking'].search([('date_to', '>', self.date_from), ('date_from', '<=', self.date_to), ('resource_id', '=', self.resource_id.id)]).ids)
        action = self.env.ref('rental.rental_booking_action_rental').read()[0]
        action['domain'] = [('id', 'in', list(overlap_ids))]
        action['name'] = _('Overlap(s) of %s') % (self.name,)
        action['context'] = {}
        return action


class RentalAgreement(models.Model):
    _name = 'rental.agreement'
    _description = "Rental Agreement"
    _order = 'create_date DESC'

    name = fields.Char("Name", required=True)
    file = fields.Binary("File", attachment=True)
    company_id = fields.Many2one('res.company', "Company", default=lambda self: self.env.company)
    content = fields.Html("Content")
    is_published = fields.Boolean('Is Published', copy=False, default=True)
