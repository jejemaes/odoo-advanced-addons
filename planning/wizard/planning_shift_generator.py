# -*- coding: utf-8 -*-

from datetime import date, datetime, timedelta
import pytz

from odoo import api, fields, models, _
from odoo.addons.resource.models.resource import float_to_time
from odoo.exceptions import UserError


class PlanningShiftGeneratorWizard(models.TransientModel):
    _name = 'planning.shift.generator'
    _description = "Planning Shift Generator"

    @api.model
    def default_get(self, fields_list):
        result = super(PlanningShiftGeneratorWizard, self).default_get(fields_list)
        if self.env.context.get('active_model') == 'planning.planning':
            result['planning_id'] = self.env.context.get('active_id')
        return result

    planning_id = fields.Many2one('planning.planning', string='Planning', required=True)
    line_ids = fields.One2many('planning.shift.generator.line', 'planning_generator_id', 'Lines')

    def action_generate(self):
        shifts_values = self.line_ids._prepare_shift_values()
        self.env['planning.shift'].create(shifts_values)
        return True


class PlanningShiftGeneratorLineWizard(models.TransientModel):
    _name = 'planning.shift.generator.line'
    _description = "Planning Shift Generator Line"

    @api.model
    def default_get(self, fields_list):
        result = super(PlanningShiftGeneratorLineWizard, self).default_get(fields_list)
        if self.env.context.get('active_model') == 'planning.planning':
            planning = self.env['planning.planning'].browse(self.env.context.get('active_id'))
            start_dt = fields.Datetime.from_string(planning.date_start)
            result['start_date'] = fields.Date.to_string(start_dt)
        return result

    planning_generator_id = fields.Many2one('planning.shift.generator', string="Generator", required=True)
    start_date = fields.Date("Start Date", required=True)
    shift_template_id = fields.Many2one('planning.shift.template', string="Template", required=True)
    number_to_generate = fields.Integer("Number to Create", required=True, default=1)

    def _prepare_shift_values(self):
        result = []
        for line in self:
            start_datetime = datetime.combine(fields.Date.from_string(line.start_date), datetime.min.time())
            local_tz = pytz.timezone(self._context.get('tz', 'UTC'))
            tz_offset = -int(start_datetime.astimezone(local_tz).utcoffset().total_seconds()/60)

            start_time = float_to_time(line.shift_template_id.start_time)
            start_datetime = start_datetime.replace(hour=start_time.hour, minute=start_time.minute)
            start_datetime = start_datetime + timedelta(minutes=tz_offset)

            duration = float_to_time(line.shift_template_id.duration)
            stop_datetime = start_datetime + timedelta(hours=duration.hour, minutes=duration.minute)


            print("##########", start_datetime)
            print(line.planning_generator_id.planning_id.date_start)
            print(start_datetime < line.planning_generator_id.planning_id.date_start)
            if start_datetime < line.planning_generator_id.planning_id.date_start:
                raise UserError(_("A shift is not include in the planning dates. All shift should start after the start date of the planning sheet."))

            i = 0
            while i < line.number_to_generate:
                values = {
                    'name': None,
                    'date_from': start_datetime,
                    'date_to': stop_datetime,
                    'template_id': line.shift_template_id.id,
                    'role_id': line.shift_template_id.role_id.id,
                    'note': line.shift_template_id.role_id.description,
                }
                values.update(line.planning_generator_id.planning_id.get_planning_data_for_shift())
                result.append(values)
                i += 1
        return result
