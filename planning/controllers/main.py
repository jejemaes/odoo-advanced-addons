# -*- coding: utf-8 -*-

import json
import pytz
from werkzeug.exceptions import NotFound, Forbidden
from werkzeug.utils import redirect

from odoo import fields, http, _
from odoo.http import request
from odoo.osv import expression
from odoo import tools


class PlanningController(http.Controller):

    @http.route(['/planning/<string:planning_token>/'], type='http', auth="public", website=True)
    def planning_public_page(self, planning_token, message=False, **kwargs):
        """ Displays an employee's calendar and the current list of open shifts """
        planning = request.env['planning.planning'].sudo().search([('access_token', '=', planning_token), ('visibility', '=', 'public')], limit=1)
        if planning:
            planning_data = self._get_planning_render_data(planning, message=message)
            return request.render('planning.planning_planning_page', planning_data)
        return request.not_found()

    @http.route(['/planning/<string:planning_token>/<string:employee_token>'], type='http', auth="public", website=True)
    def planning_private_page(self, planning_token, employee_token, message=False, **kwargs):
        planning = request.env['planning.planning'].sudo().search([('access_token', '=', planning_token)], limit=1)
        if planning:
            employee_sudo = request.env['hr.employee'].sudo().search([('employee_token', '=', employee_token)], limit=1)
            if employee_sudo:
                planning_data = self._get_planning_render_data(planning, employee=employee_sudo, message=message)
                return request.render('planning.planning_planning_page', planning_data)
        return request.not_found()

    @http.route('/planning/<string:token_planning>/<string:token_employee>/assign/<int:shift_id>', type="http", auth="public")
    def planning_self_assign(self, token_planning, token_employee, shift_id, message=False, **kwargs):
        planning_sudo = request.env['planning.planning'].sudo().search([('access_token', '=', token_planning)], limit=1)
        if not planning_sudo:
            return request.not_found()

        domain = planning_sudo.get_shift_domain()
        domain = expression.AND([domain, [('id', '=', shift_id)]])
        shift_sudo = request.env['planning.shift'].sudo().search(domain, limit=1)
        if not shift_sudo.exists():
            return request.not_found()

        employee_sudo = request.env['hr.employee'].sudo().search([('employee_token', '=', token_employee)], limit=1)
        if not employee_sudo:
            return request.not_found()

        if not shift_sudo.company_id.planning_allow_self_assign:
            raise Forbidden()

        if shift_sudo.employee_id:
            return redirect('/planning/%s/%s?message=%s' % (token_planning, token_employee, 'already_assign'))

        shift_sudo.write({'employee_id': employee_sudo.id})
        if message:
            return redirect('/planning/%s/%s?message=%s' % (token_planning, token_employee, 'assign'))
        return redirect('/planning/%s/%s' % (token_planning, token_employee))

    @http.route('/planning/<string:token_planning>/<string:token_employee>/unassign/<int:shift_id>', type="http", auth="public")
    def planning_self_unassign(self, token_planning, token_employee, shift_id, message=False, **kwargs):
        planning_sudo = request.env['planning.planning'].sudo().search([('access_token', '=', token_planning)], limit=1)
        if not planning_sudo:
            return request.not_found()

        domain = planning_sudo.get_shift_domain()
        domain = expression.AND([domain, [('id', '=', shift_id)]])
        shift_sudo = request.env['planning.shift'].sudo().search(domain, limit=1)
        if not shift_sudo.exists():
            return request.not_found()

        employee_sudo = request.env['hr.employee'].sudo().search([('employee_token', '=', token_employee)], limit=1)
        if not employee_sudo:
            return request.not_found()

        if not shift_sudo.company_id.planning_allow_self_unassign:
            raise Forbidden()

        if shift_sudo.employee_id != employee_sudo:  # only unassing its own shifts
            raise Forbidden()

        shift_sudo.write({'employee_id': False})
        if message:
            return redirect('/planning/%s/%s?message=%s' % (token_planning, token_employee, 'unassign'))
        return redirect('/planning/%s/%s' % (token_planning, token_employee))

    @http.route(['/planning/<string:planning_token>/employees'], type='http', auth="public", methods=['GET'], website=True, sitemap=False)
    def planning_collaborative_employees(self, planning_token, query='', limit=25, **kwargs):
        planning = request.env['planning.planning'].sudo().search([('access_token', '=', planning_token)], limit=1)
        if planning:
            if planning.is_collaborative:
                employee_data = request.env['hr.employee'].sudo().search_read(
                    domain=[('name', '=ilike', (query or '') + "%"), ('id', 'in', planning.employee_ids.ids)],
                    fields=['id', 'display_name'],
                    limit=int(limit),
                )
                return json.dumps(employee_data)
        return request.not_found()

    @http.route(['/planning/<string:planning_token>/collaborative/assign/'], type='http', auth="public", methods=['POST'], website=True)
    def planning_collaborative_assign(self, planning_token, **kw):
        planning = request.env['planning.planning'].sudo().search([('access_token', '=', planning_token)], limit=1)
        if planning:
            if planning.is_collaborative:
                domain = planning.get_shift_domain()
                shift_ids = request.env['planning.shift'].sudo().search(domain).ids
                try:
                    shift_id = int(kw['shift_id'])
                    employee_id = int(kw['employee_id'])
                    if shift_id in shift_ids:
                        request.env['planning.shift'].sudo().browse(shift_id).write({'employee_id': employee_id})
                        return request.redirect('/planning/%s/?message=collaborative_assign' % (planning.access_token,))
                except (KeyError, ValueError) as e:
                    pass
        return request.not_found()

    @http.route(['/planning/<string:planning_token>/collaborative/unassign/'], type='http', auth="public", methods=['POST'], website=True)
    def planning_collaborative_unassign(self, planning_token, **kw):
        planning = request.env['planning.planning'].sudo().search([('access_token', '=', planning_token)], limit=1)
        if planning:
            if planning.is_collaborative:
                domain = planning.get_shift_domain()
                shift_ids = request.env['planning.shift'].sudo().search(domain).ids
                try:
                    shift_id = int(kw['shift_id'])
                    if shift_id in shift_ids:
                        request.env['planning.shift'].sudo().browse(shift_id).write({'employee_id': None})
                        return request.redirect('/planning/%s/?message=collaborative_unassign' % (planning.access_token,))
                except (KeyError, ValueError) as e:
                    pass
        return request.not_found()

    def _get_planning_render_data(self, planning, employee=None, message=False):
        planning_sudo = planning.sudo()

        # HACK: take the responsible TZ in order to avoid tz conversion in frontend
        # When no employee, as the page is rendered serverside, we don't know the borwser
        # timezone (neither the one of the current employee or user), so we use the one
        # from the responsible.
        employee_tz = pytz.timezone(request.env.context.get('tz', 'UTC'))
        if planning_sudo.user_id and planning_sudo.user_id.tz:
            employee_tz = pytz.timezone(planning_sudo.user_id.tz)
        if employee and employee.tz:
            employee_tz = pytz.timezone(employee.tz)

        # get shifts to include in the calendar
        domain = planning_sudo.get_shift_domain()
        shifts = request.env['planning.shift']
        if planning_sudo.visibility == 'invited_see_own':
            subdomain = [('employee_id', '=', employee.id)]
            if planning_sudo.include_open_shift:
                subdomain = expression.OR([subdomain, [('employee_id', '=', False)]])
            domain = expression.AND([domain, subdomain])

        shifts = request.env['planning.shift'].sudo().search(domain)

        open_shifts_data = []
        assigned_shifts_data = []
        for shift in shifts:
            if planning_sudo.date_start <= shift.date_from <= planning_sudo.date_stop:
                if shift.employee_id:
                    assigned_shifts_data.append(self._get_planning_shift_render_data(shift, planning_sudo, employee))
                else:
                    open_shifts_data.append(self._get_planning_shift_render_data(shift, planning_sudo, employee))

        open_shifts_data.sort(key=lambda item: item['start_utc'])

        return {
            'planning': planning_sudo,
            'planning_shift_count': planning_sudo.shift_count,
            'planning_date_start':planning_sudo.date_start,
            'planning_date_stop': planning_sudo.date_stop,
            'planning_collaborative_employee_url': '/planning/%s/employees' % (planning_sudo.access_token,) if planning.is_collaborative else None,
            'open_shifts_data': open_shifts_data,
            'assigned_shifts_data': assigned_shifts_data + open_shifts_data,
            'employee': employee,
            'message_slug': message,
            'locale': tools.get_lang(request.env).iso_code.split("_")[0],
            'format_datetime': lambda dt, dt_format: tools.format_datetime(request.env, fields.Datetime.from_string(dt), tz=employee_tz.zone, dt_format=dt_format),
        }

    def _get_planning_shift_render_data(self, shift, planning_sudo, employee=None):
        """ Note: the returned dict MUST BE serializable. So no browse record should be set as value. """
        title = shift.name
        if planning_sudo.visibility != 'invited_see_own':
            title = shift.role_id.name
            if shift.employee_id:
                title += ' (%s)' % (shift.employee_id.name,)

        return {
            'id': shift.id,
            'title': title,
            'name': shift.name,
            'start_utc': fields.Datetime.to_string(shift.date_from),
            'end_utc': fields.Datetime.to_string(shift.date_to),
            'color': self._format_planning_shifts(shift.role_id.color),
            'shift_id': shift.id,
            'duration': tools.format_duration((shift.date_to - shift.date_from).total_seconds() / 60*60),
            'note': shift.note,
            'employee_id': shift.employee_id.id if shift.employee_id else False,
            'employee_name': shift.employee_id.name if shift.employee_id else False,
            'can_self_assign': employee and shift.can_self_assign,
            'can_self_unassign': employee and shift.employee_id == employee and shift.company_id.planning_allow_self_assign,
            'can_self_assign_url': '/planning/%s/%s/assign/%s' % (planning_sudo.access_token, employee.employee_token, shift.id) if employee else False,
            'can_self_unassign_url': '/planning/%s/%s/unassign/%s' % (planning_sudo.access_token, employee.employee_token, shift.id) if employee else False,
            'collaborative_employee_url': "/planning/%s/employees/" % (planning_sudo.access_token,) if planning_sudo.is_collaborative else False,
            'role_name': shift.role_id.name if shift.role_id else None,
            'role_description': shift.role_id.description if shift.role_id else None,
        }

    def _format_planning_shifts(self, color_code):
        switch_color = {
            0: '#008784',   # No color (doesn't work actually...)
            1: '#EE4B39',   # Red
            2: '#F29648',   # Orange
            3: '#F4C609',   # Yellow
            4: '#55B7EA',   # Light blue
            5: '#71405B',   # Dark purple
            6: '#E86869',   # Salmon pink
            7: '#008784',   # Medium blue
            8: '#267283',   # Dark blue
            9: '#BF1255',   # Fushia
            10: '#2BAF73',  # Green
            11: '#8754B0'   # Purple
        }
        return switch_color[color_code]
