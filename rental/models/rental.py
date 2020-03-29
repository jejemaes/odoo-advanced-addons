# -*- coding: utf-8 -*-

from datetime import date, datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class RentalBooking(models.Model):
    _name = 'rental.booking'
    _rec_name = 'code'
    _description = 'Rental Reservation'
    _order = 'date_from desc'
    _inherit = ['mail.activity.mixin']
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

    resource_time_id = fields.Many2one('resource.calendar.leaves', string="Time Entry", required=True, domain=[('time_type', '=', 'rental')], auto_join=True, ondelete='cascade')
    time_type = fields.Selection(related='resource_time_id.time_type', inherited=True, default='rental')
    resource_id = fields.Many2one(related='resource_time_id.resource_id', inherited=True, domain=[('resource_type', '=', 'material')], states={'reserved': [('readonly', True)], 'picked_up': [('readonly', True)], 'returned': [('readonly', True)], 'done': [('readonly', True)]}, string="Equipment", required=True)
    resource_color = fields.Integer(related='resource_time_id.resource_id.color')

    date_from = fields.Datetime(default=_default_date_from, inherited=True, related='resource_time_id.date_from', states={'reserved': [('readonly', True)], 'picked_up': [('readonly', True)], 'returned': [('readonly', True)], 'done': [('readonly', True)]})
    date_to = fields.Datetime(default=_default_date_to, inherited=True, related='resource_time_id.date_from', states={'reserved': [('readonly', True)], 'picked_up': [('readonly', True)], 'returned': [('readonly', True)], 'done': [('readonly', True)]})

    code = fields.Char('Reference', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, copy=False)
    partner_shipping_id = fields.Many2one('res.partner', string='Delivery Address', copy=False, help="Delivery address for current booking.")
    user_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self.env.user, index=True)
    state = fields.Selection([
        ('draft', 'Request'),
        ('reserved', 'Reserved'),
        ('picked_up', 'Picked Up'),
        ('returned', 'Returned'),
        ('done', 'Done'),
        ('cancel', 'Cancel'),
    ], string='Status', default='draft', required=True, copy=False)
    duration_hours = fields.Float('Duration in Hours', compute='_compute_durations')
    duration_days = fields.Float('Duration in Days', compute='_compute_durations')
    overlap_count = fields.Integer("Number of rental overlapping", compute='_compute_overlap_count')

    note = fields.Text('Internal Notes', copy=False)
    agreement_id = fields.Many2one('rental.agreement', string="Agreement", default=_default_agreement_id, copy=False)

    @api.depends('resource_time_id.resource_id', 'resource_time_id.date_from', 'resource_time_id.date_to')
    def _compute_durations(self):
        for rental in self:
            duration_data = rental.resource_id.get_work_days_data(fields.Datetime.from_string(rental.resource_time_id.date_from), fields.Datetime.from_string(rental.resource_time_id.date_to))
            rental.duration_hours = duration_data['hours']
            rental.duration_days = duration_data['days']

    @api.depends('resource_time_id.date_from', 'resource_time_id.date_to')
    def _compute_overlap_count(self):
        overlap_count_map = {}
        if self.ids:
            query = """
                SELECT t.time_id AS time_id, COUNT(t.time_overlap_id) AS overlap_count
                FROM (
                    SELECT R1.id AS time_id, R2.id AS time_overlap_id
                    FROM resource_calendar_leaves R1
                        INNER JOIN resource_calendar_leaves R2 ON (R1.date_to > R2.date_from AND R1.date_from < R2.date_to AND R1.id != R2.id)
                    WHERE R1.time_type = 'rental'
                        AND R2.time_type = 'rental'
                        AND R1.resource_id = R2.resource_id
                        AND R1.id IN %s
                ) AS t
                GROUP BY t.time_id
            """
            self.env.cr.execute(query, (tuple(self.mapped('resource_time_id').ids),))
            data = self.env.cr.dictfetchall()
            overlap_count_map = {item['time_id']: item['overlap_count'] for item in data}

        for shift in self:
            shift.overlap_count = overlap_count_map.get(shift.resource_time_id.id, 0)

    @api.onchange('resource_id')
    def onchange_resource(self):
        if self.resource_id:
            self.calendar_id = self.resource_id.calendar_id

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            addr = self.partner_id.address_get(['delivery'])
            self.partner_shipping_id = addr['delivery']

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
        return super(RentalBooking, self).create(value_list)

    def write(self, values):
        if 'date_from' in values or 'date_to' in values:
            states = self.mapped('state')
            if any([state in states for state in ['reserved', 'picked_up', 'returned', 'done']]):
                raise UserError(_('You can not change the dates of a none draft booking'))
        return super(RentalBooking, self).write(values)

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
        self.write({'state': 'cancel'})

    def action_reset(self):
        self.write({'state': 'draft'})

    def action_view_overlap(self):
        overlap_ids = set(self.env['rental.booking'].search([('date_to', '>=', self.date_from), ('date_from', '<=', self.date_to), ('resource_id', '=', self.resource_id.id)]).ids)
        action = self.env.ref('rental.rental_booking_action_rental').read()[0]
        action['domain'] = [('id', 'in', list(overlap_ids))]
        action['name'] = _('Overlap(s) of %s') % (self.name,)
        return action

    # ---------------------------------------------------------
    # Business Methods
    # ---------------------------------------------------------

    def message_subscribe(self, partner_ids):
        """ Hack to make the activity mixin work without inheriting of mail thread """
        return False


class RentalAgreement(models.Model):
    _name = 'rental.agreement'
    _description = "Rental Agreement"
    _order = 'create_date DESC'

    name = fields.Char("Name", required=True)
    attachment_id = fields.Many2one('ir.attachment', "File", required=True, domain=[('mimetype', '=', 'application/pdf')], auto_join=True)
    company_id = fields.Many2one('res.company', "Company", related='attachment_id.company_id', readonly=False)
    note = fields.Text("Note")
    public = fields.Boolean(related='attachment_id.public', readonly=False, default=True)
