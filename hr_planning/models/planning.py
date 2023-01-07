# -*- coding: utf-8 -*-

from datetime import date, datetime, timedelta
import pytz
import uuid

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import format_date, format_datetime


class Planning(models.Model):
    _inherit = 'planning.planning'

    visibility = fields.Selection([
        ('public', 'Public'),
        ('invited_see_all', 'Invited and See All Shifts'),
        ('invited_see_own', 'Invited and See Only His Shifts')
    ], string='Visibility', required=True, default='invited_see_own', help="""
        Anyone with the link can see public planning. \n
        'Invited and See all shifts' required to be invited to see the all planning. \n
        'Invited and See only his shifts' required to be invited to see its own planning shifts.
    """)
    is_collaborative = fields.Boolean("Collaborative Mode", default=False, required=True)
    employee_ids = fields.Many2many('hr.employee', string="Employees")
    planning_url = fields.Char("Shared URL", compute='_compute_planning_url')
    last_sent_date = fields.Datetime("Last Publication Date", copy=False, readonly=True)

    @api.depends('visibility', 'access_token')
    def _compute_planning_url(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        for planning in self:
            if planning.visibility == 'public':
                planning.planning_url = '%s/planning/%s' % (base_url, planning.access_token,)
            else:
                planning.planning_url = False

    @api.onchange('visibility')
    def _onchange_visibility(self):
        if self.visibility != 'public':
            self.is_collaborative = False

    @api.onchange('is_collaborative')
    def _onchange_is_collaborative(self):
        if not self.is_collaborative:
            self.employee_ids = None

    # ----------------------------------------------------------------------------
    # Actions
    # ----------------------------------------------------------------------------

    def action_publish(self):
        self.env['planning.shift'].search(self.get_shift_domain()).write({'publication_date': fields.Datetime.now()})

    # ----------------------------------------------------------------------------
    # Business Methods
    # ----------------------------------------------------------------------------

    def _send_planning(self, message=None, employees=False):
        email_from = self.env.user.email or self.env.user.company_id.email or ''
        sent_shifts = self.env['planning.shift']
        for planning in self:
            # prepare planning urls, recipient employees, ...
            shifts = self.env['planning.shift'].search(planning.get_shift_domain())
            open_shifts = shifts.filtered(lambda shift: not shift.employee_id) if planning.include_open_shift else 0

            # extract planning URLs
            employees = employees or shifts.mapped('employee_id')
            employee_url_map = employees.sudo()._planning_get_url(planning)

            # send planning email template with custom domain per employee
            template = self.env.ref('planning.email_template_planning_planning', raise_if_not_found=False)
            template_context = {
                'shift_unassigned_count': open_shifts and len(open_shifts),
                'shift_total_count': shifts and len(shifts),
                'message': message,
            }
            if template:
                # /!\ For security reason, we only given the public employee to render mail template
                for employee in self.env['hr.employee.public'].browse(employees.ids):
                    if employee.work_email:
                        template_context['employee'] = employee
                        destination_tz = pytz.timezone(self.env.user.tz or 'UTC')
                        template_context['start_datetime'] = pytz.utc.localize(planning.date_start).astimezone(destination_tz).replace(tzinfo=None)
                        template_context['end_datetime'] = pytz.utc.localize(planning.date_stop).astimezone(destination_tz).replace(tzinfo=None)
                        template_context['planning_url'] = employee_url_map[employee.id]
                        template.with_context(**template_context).send_mail(planning.id, email_values={'email_to': employee.work_email, 'email_from': email_from}, notif_layout='mail.mail_notification_light')
            sent_shifts |= shifts

            shifts.action_mark_as_published()
        # mark as sent
        self.write({'last_sent_date': fields.Datetime.now()})
        return True
