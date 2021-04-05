odoo.define('web_gantt.GanttView', function (require) {
"use strict";

var AbstractView = require('web.AbstractView');
var BasicView = require('web.BasicView');

var core = require('web.core');
var session = require('web.session');
var GanttModel = require('web_gantt.GanttModel');
var GanttRenderer = require('web_gantt.GanttRenderer');
var GanttController = require('web_gantt.GanttController');
var view_registry = require('web.view_registry');
var pyUtils = require('web.py_utils');

var _t = core._t;
var _lt = core._lt;

// determine locale file to load
var locales_mapping = {
    'ar_SY': 'ar', 'ca_ES': 'ca', 'zh_CN': 'cn', 'cs_CZ': 'cs', 'da_DK': 'da',
    'de_DE': 'de', 'el_GR': 'el', 'es_ES': 'es', 'fi_FI': 'fi', 'fr_FR': 'fr',
    'he_IL': 'he', 'hu_HU': 'hu', 'id_ID': 'id', 'it_IT': 'it', 'ja_JP': 'jp',
    'ko_KR': 'kr', 'nl_NL': 'nl', 'nb_NO': 'no', 'pl_PL': 'pl', 'pt_PT': 'pt',
    'ro_RO': 'ro', 'ru_RU': 'ru', 'sl_SI': 'si', 'sk_SK': 'sk', 'sv_SE': 'sv',
    'tr_TR': 'tr', 'uk_UA': 'ua',
    'ar': 'ar', 'ca': 'ca', 'zh': 'cn', 'cs': 'cs', 'da': 'da', 'de': 'de',
    'el': 'el', 'es': 'es', 'fi': 'fi', 'fr': 'fr', 'he': 'he', 'hu': 'hu',
    'id': 'id', 'it': 'it', 'ja': 'jp', 'ko': 'kr', 'nl': 'nl', 'nb': 'no',
    'pl': 'pl', 'pt': 'pt', 'ro': 'ro', 'ru': 'ru', 'sl': 'si', 'sk': 'sk',
    'sv': 'sv', 'tr': 'tr', 'uk': 'ua',
};
var current_locale = session.user_context.lang || 'en_US';
var current_short_locale = current_locale.split('_')[0];
var locale_code = locales_mapping[current_locale] || locales_mapping[current_short_locale];
var locale_suffix = locale_code !== undefined ? '_' + locale_code : '';

var GanttView = BasicView.extend({
    cssLibs: [
        "/web_gantt/static/lib/dhtmlxGantt/codebase/dhtmlxgantt.css",
        "/web_gantt/static/lib/dhtmlxGantt/codebase/skins/dhtmlxgantt_material.css",
    ],
    jsLibs: [
        "/web_gantt/static/lib/dhtmlxGantt/codebase/dhtmlxgantt.js",
        "/web_gantt/static/lib/dhtmlxGantt/codebase/ext/dhtmlxgantt_click_drag.js",
        "/web_gantt/static/lib/dhtmlxGantt/codebase/locale/locale" + locale_suffix + ".js"
    ],
    display_name: _lt('Gantt'),
    icon: 'fa-tasks',
    config: _.extend({}, BasicView.prototype.config, {
        Model: GanttModel,
        Controller: GanttController,
        Renderer: GanttRenderer,
    }),
    viewType: 'gantt',
    mobile_friendly: false,

    /**
     * @override
     */
    init: function (viewInfo, params) {
        var self = this;
        this._super.apply(this, arguments);

        var arch = this.arch;
        var fields = this.fields;

        var canPlan = this.arch.attrs.plan ? !!JSON.parse(this.arch.attrs.plan) : false;

        // Scales and precisions
        this.SCALES = {
            day: { string: _t('Day'), defaultUnitPrecision: 'hour:full', allowedUnitPrecision: {hour: ['full', 'half', 'quarter']} },
            week: { string: _t('Week'), defaultUnitPrecision: 'day:full', allowedUnitPrecision: {hour: ['full'], day: ['full', 'half']} },
            month: { string: _t('Month'), defaultUnitPrecision: 'day:full', allowedUnitPrecision: {day: ['full'], week: ['full']} },
            year: { string: _t('Year'), defaultUnitPrecision: 'month:full', allowedUnitPrecision: {week: ['full'], month: ['full']} },
        };

        // Cell precision
        // precision = {'day': 'hour:half', 'week': 'day:half', 'month': 'day', 'year': 'month:quarter'}
        var precisionAttrs = arch.attrs.precision ? pyUtils.py_eval(arch.attrs.precision) : {};
        var cellPrecisions = {};
        _.each(this.SCALES, function (vals, key) {
            if (precisionAttrs[key]) {
                // set default value
                var defaultUntiPrecision = vals.defaultUnitPrecision.split(':');
                cellPrecisions[key] = {unit: defaultUntiPrecision[0], precision: defaultUntiPrecision[1]};

                // set the unit from attrs
                var unitPrecision = precisionAttrs[key].split(':'); // hour:half
                if (unitPrecision[0] && _.contains(_.keys(vals.allowedUnitPrecision), unitPrecision[0])) {
                    cellPrecisions[key].unit = unitPrecision[0];
                } else {
                    console.error("Unit incompatible with scale; unit=", unitPrecision, "  scale=", key);
                }

                // set the precision from attrs
                if (unitPrecision[1] && _.contains(vals.allowedUnitPrecision[unitPrecision[0]], unitPrecision[1])) {
                    cellPrecisions[key].precision = unitPrecision[1];
                } // otherwise, keep default precision
            }
        });

        // Allowed scales
        var allowedScales;
        if (arch.attrs.scales) {
            var possibleScales = Object.keys(this.SCALES);
            allowedScales = _.reduce(arch.attrs.scales.split(','), function (allowedScales, scale) {
                if (possibleScales.indexOf(scale) >= 0) {
                    allowedScales.push(scale.trim());
                }
                return allowedScales;
            }, []);
        } else {
            allowedScales = Object.keys(this.SCALES);
        }

        // Color and progress fields
        var colorField = arch.attrs.color;
        var progressField = arch.attrs.progress;

        // Decoration fields
        var decorationFields = [];
        _.each(arch.children, function (child) {
            if (child.tag === 'field') {
                decorationFields.push(child.attrs.name);
            }
        });

        // Initial date and scale
        var scale = arch.attrs.default_scale || params.context.gantt_scale || 'month';
        var initialDate = moment(params.initialDate || params.context.gantt_initial_date || new Date());
        var offset = arch.attrs.offset;
        if (offset && scale) {
            initialDate.add(offset, scale);
        }

        // form view which is opened by gantt
        var formViewId = arch.attrs.form_view_id ? parseInt(arch.attrs.form_view_id, 10) : false;
        if (params.action && !formViewId) { // fallback on form view action, or 'false'
            var result = _.findWhere(params.action.views, { type: 'form' });
            formViewId = result ? result.viewID : false;
        }
        var dialogViews = [[formViewId, 'form']];

        // use date or datetime
        var useDateOnly = viewInfo.fields[arch.attrs.date_start].type == 'date'

        this.loadParams.fields = fields;
        this.loadParams.scale = scale;
        this.loadParams.dateStartField = arch.attrs.date_start;
        this.loadParams.dateStopField = arch.attrs.date_stop;
        this.loadParams.colorField = colorField;
        this.loadParams.progressField = progressField;
        this.loadParams.decorationFields = decorationFields;
        this.loadParams.initialDate = initialDate;
        this.loadParams.fields = this.fields;
        this.loadParams.defaultGroupBy = this.arch.attrs.default_group_by;
        this.loadParams.useDateOnly = useDateOnly;

        this.controllerParams.context = params.context || {};
        this.controllerParams.title = params.action ? params.action.name : _t("Gantt");
        this.controllerParams.SCALES = this.SCALES;
        this.controllerParams.allowedScales = allowedScales;
        this.controllerParams.dialogViews = dialogViews;
        this.controllerParams.cellPrecisions = cellPrecisions;
        this.controllerParams.canPlan = canPlan && this.controllerParams.activeActions.edit;
        this.controllerParams.useDateOnly = useDateOnly;

        this.rendererParams.canCreate = this.controllerParams.activeActions.create;
        this.rendererParams.canEdit = this.controllerParams.activeActions.edit;
        this.rendererParams.fieldsInfo = viewInfo.fields;
        this.rendererParams.SCALES = this.SCALES;
        this.rendererParams.cellPrecisions = cellPrecisions;
        this.rendererParams.string = arch.attrs.string || _t('Gantt View');
        this.rendererParams.colorField = colorField;
        this.rendererParams.progressField = progressField;
        this.rendererParams.canPlan = canPlan && this.controllerParams.activeActions.edit;
        this.rendererParams.useDateOnly = useDateOnly;
    },
});

view_registry.add('gantt', GanttView);

return GanttView;

});
