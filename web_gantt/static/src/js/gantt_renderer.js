/** @odoo-module */

import { getBundle, loadBundle, loadJS } from "@web/core/assets";
import { browser } from "@web/core/browser/browser";
import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { evaluateExpr } from "@web/core/py_js/py";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { useDebounced } from "@web/core/utils/timing";
import { Component, onWillUnmount, useEffect, useRef, onWillStart, onMounted, onWillUpdateProps, onWillDestroy} from "@odoo/owl";
const { DateTime } = luxon;


// server format expressed in DHX specification
// https://docs.dhtmlx.com/gantt/desktop__date_format.html
// so, we can use `serializeDate`
const DHX_DATE_FORMAT = "%Y-%m-%d";
const DHX_TIME_FORMAT = "%H:%i:%s";
const DHX_DATETIME_FORMAT = `${DHX_DATE_FORMAT} ${DHX_TIME_FORMAT}`;


const localesMapping = {
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

export class GanttRenderer extends Component {

    static props = {
        model: Object,
        openDialog: Function,
        archInfo: Object,
    };
    static template = "web_gantt.GanttRenderer";

	setup() {
        this.model = this.props.model;
        this.decorationMap = this.model.metaData.archInfo.decorationMap;
        this.activeActions = this.model.metaData.archInfo.activeActions;
        this.fieldInfos = this.model.metaData.fields;

        // DHX Gantt Lib
        this.dhxGantt = null;
        this.dhxSetup = false;

        // hooks
        this.containerRef = useRef("container");
        this.userService = useService("user");
        this.onResize = useDebounced(this.renderGantt, 200);
        this.debounceOnTaskClick = useDebounced(this._dhxOnTaskClick, 200);

        // user lang
        const currentLocale = this.userService.lang || 'en_US';
        const currentShortLocale = currentLocale.split('_')[0];
        const localeCode = localesMapping[currentLocale] || localesMapping[currentShortLocale];
        const localeSuffix = localeCode !== undefined ? '_' + localeCode : '';

        onWillStart(async () => {
            await loadBundle({
                jsLibs: [
                    "/web_gantt/static/lib/dhtmlxGantt/codebase/dhtmlxgantt.js",
                    "/web_gantt/static/lib/dhtmlxGantt/codebase/ext/dhtmlxgantt_click_drag.js",
                    "/web_gantt/static/lib/dhtmlxGantt/codebase/locale/locale" + localeSuffix + ".js"
                ],
                cssLibs: [
                    "/web_gantt/static/lib/dhtmlxGantt/codebase/dhtmlxgantt.css",
                    "/web_gantt/static/lib/dhtmlxGantt/codebase/skins/dhtmlxgantt_material.css",
                ],
            });
            this.dhxGantt = window.gantt; // since bundle is loaded
        });

        useEffect(() => this.renderGantt());
        onMounted(this.onMounted);
        onWillUnmount(this.onWillUnmount);
    }

    onMounted() {
        // bind dhx events
        this.onTaskDblClick = gantt.attachEvent("onTaskDblClick", function(id, e){
            return false; // prevent lightbox to open
        });
        this.onTaskClick = this.dhxGantt.attachEvent("onTaskClick", this.debounceOnTaskClick.bind(this));
        this.afterTaskDragEvent = this.dhxGantt.attachEvent("onAfterTaskDrag", this._dhxOnAfterTaskDrag.bind(this));

        // refresh the gantt part when resizing window
        browser.addEventListener("resize", this.onResize);
    }

    onWillUnmount() {
        // Note: DO NOT destroy the gantt object (unbind events, clear data, out of DOM, ...)
        // by calling `this.dhxGantt.destructor();`.

        // unbind onMounted bindings
        this.dhxGantt.detachEvent(this.onTaskClick);
        this.dhxGantt.detachEvent(this.afterTaskDragEvent);
        this.dhxGantt.detachEvent(this.onTaskDblClick);

        // unbind the refreshing
        browser.removeEventListener("resize", this.onResize);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    get canCreate() {
        return this.activeActions.create;
    }
    get canEdit() {
        return this.activeActions.edit;
    }

    get progressField() {
        return this.model.progressField;
    }

    get rows() {
        const rows = [];

        const serializerFunc = this.useDateOnly ? serializeDate : serializeDateTime;

        const processNode = (node) => {
            if (node.isGroup) {
                rows.push({
                    id: node.groupId,
                    text: node.name,
                    open: true,
                    parent: node.parentGroupId,
                    type: gantt.config.types.project,
                    duration: 0, // this will set the "consolidation" pill according the child tasks. Anyway, we don't display it.
                    context: node.context,
                });
                for (const subNode of node.childNodes || []) {
                    processNode(subNode);
                }
            } else {
                const parentId = node.parentGroupId;
                for (const recordId of node.recordIds || []) {
                    const record = this.model.recordMap[recordId];
                    rows.push({
                        id: _.uniqueId('record'),
                        text: record.display_name,
                        open: true,
                        parent: node.parentGroupId,
                        type: gantt.config.types.task,
                        start_date: serializerFunc(record[this.model.dateStartField]),
                        end_date: serializerFunc(record[this.model.dateStopField]),
                        progress: this.progressField ? record[this.progressField] / 100 : null,
                        // odoo stuffs
                        color: this.model.colorField ? record[this.model.colorField] : null,
                        context: node.context,
                        record: record,
                        evalContext: this._getEvalContext(record),
                    });
                }
            }
        };

        for (const node of this.model.groupTree) {
            processNode(node);
        }
        return rows;
    }

    get useDateOnly() {
        return this.model.useDateOnly;
    }

    /**
     * Instantiates a Chart (Chart.js lib) to render the graph according to
     * the current config.
     */
    renderGantt() {
        // Haskish way of setting the parent div size, as dhtmlx is using 'px' and not relative %. This
        // is not responsive.
        this.containerRef.el.style.height = `${document.body.clientHeight}px`;
        this.containerRef.el.style.width = `${document.body.clientWidth}px`;

        if (!this.dhxSetup){
            this._setUpDhxGantt();
            this._setUpDhxZoomScales();
        }
        // update range
        this.dhxGantt.config.start_date = this.model.metaData.startDate;
        this.dhxGantt.config.end_date = this.model.metaData.stopDate;

        // init gantt and extensions
        this.dhxGantt.init("gantt_wrapper");
        this.dhxGantt.ext.zoom.setLevel(this.model.metaData.scale.id);
        this.dhxGantt.clearAll(); // as the renderer is not destroy each refresh, we need to clear the data in DHX
		this.dhxGantt.parse({
			data: this.rows,
			links: []
		});
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @param {Object} record: alreay parsed record (date are luxon datetime)
     * @retuns {Object}
     */
    _getEvalContext(record) {
        const context = Object.assign({}, this.userService.context);
        for (const [fieldName, value] of Object.entries(record)) {
            context[fieldName] = value;
        }
        return context;
    }

    /**
     * @private
     * note: setup is static, the config should not depends on model. It is not reloaded.
     */
    _setUpDhxGantt() {
        // time format
        const { weekStart } = localization;
        this.dhxGantt.config.start_on_monday = weekStart === 1;
        if (this.model.useDateOnly) {  // date
            this.dhxGantt.config.xml_date = DHX_DATE_FORMAT;
            this.dhxGantt.config.date_format = DHX_DATE_FORMAT;
            this.dhxGantt.config.duration_unit = "day";
            this.dhxGantt.config.duration_step = 1;
            this.dhxGantt.config.server_utc = true;
        } else { // datetime
            this.dhxGantt.config.xml_date = DHX_DATETIME_FORMAT;
            this.dhxGantt.config.date_format = DHX_DATETIME_FORMAT;
            this.dhxGantt.config.duration_unit = "minute";
            this.dhxGantt.config.duration_step = 15;
            this.dhxGantt.config.server_utc = true; // make the gantt lib use UTC dates as input and output
        }

        // ui
        this.dhxGantt.config.scale_height = 75;
        this.dhxGantt.config.autosize = "y";
        const columns = [{
            name: "text",
            label: this.model.metaData.archInfo.viewTitle,
            tree: true,
            width: '*',
            resize: true,
        }];
        if (!!this.progressField) {
            columns.push({
                name:"progress",
                label: _t("Progress"),
                align:"right",
                template:function(obj){ return sprintf('%s %', Math.round(obj.progress * 1000) / 10)}
            });
        }
        this.dhxGantt.config.columns = columns;
        this.dhxGantt.config.initial_scroll = false;
        this.dhxGantt.config.preserve_scroll = true;
        this.dhxGantt.config.show_progress = !!this.progressField;

        // templates
        var self = this;
        this.dhxGantt.templates.timeline_cell_class = function(row, date){
            var classes = '';
            // style for today cell column
            var today = new Date();
            if (self.model.metaData.scale.id !== "day" && date.getDate() === today.getDate() && date.getMonth() === today.getMonth() && date.getYear() === today.getYear()) {
                classes += " o_today";
            }
            return classes;
        };
        this.dhxGantt.templates.task_class = this._dhxTaskClass.bind(this);

        // drag options
        this.dhxGantt.config.drag_resize = this.canEdit; // allow resize gantt task
        this.dhxGantt.config.drag_move = this.canEdit; // allow moving gantt task
        this.dhxGantt.config.drag_links = false;
        this.dhxGantt.config.drag_progress = !!this.progressField && this.canEdit && !this.model.fieldInfos[this.progressField].readonly; // allow changing progress
        this.dhxGantt.config.multiselect = false;
        if (this.canCreate) {
            this.dhxGantt.config.click_drag = {
                callback: this._dhxDrag.bind(this),
                singleRow: true,
            };
        }

        // mark as setup
        this.dhxSetup = true;
    }

    /**
     * @private
     * Transform `allowedScales` into DHX `zoom` config to initialize the extension.
     * Note: setup is static, the config should not depends on model. It is not reloaded.
     */
    _setUpDhxZoomScales() {
        const zoomLevels = [];
        for (const [scaleId, scaleInfo] of Object.entries(this.model.allowedScales)) {
            const scales = [];
            switch (scaleId) {
                case "day":
                    if (scaleInfo.cellUnit == 'hour') {
                        scales.push({unit: 'hour', step: 24, format: "%D %d %M"});
                        switch (scaleInfo.cellPrecision) {
                            case "full":
                                scales.push({unit: 'minute', step: 60, format: "%h %a"});
                                break;
                            case "half":
                                scales.push({unit: 'hour', step: 1, format: "%h %a"});
                                scales.push({unit: 'minute', step: 30, format: "%i"});
                                break;
                            case "quarter":
                                scales.push({unit: 'hour', step: 1, format: "%h %a"});
                                scales.push({unit: 'minute', step: 15, format: "%i"});
                                break;
                        }
                    }
                    break;
                case "week":
                    if (scaleInfo.cellUnit == 'day') {
                        switch (scaleInfo.cellPrecision) {
                            case "full":
                                scales.push({unit: 'hour', step: 24, format: "%D %d %M"});
                                break;
                            case "half":
                                scales.push({unit: 'day', step: 1, format: "%D %d %M"});
                                scales.push({unit: 'hour', step: 12, format: "%h %a"});
                                break;
                        }
                    }
                    if (scaleInfo.cellUnit == 'hour') {
                        if (scaleInfo.cellPrecision == 'full') {
                            scales.push({unit: 'day', step: 1, format: "%D %d %M"});
                            scales.push({unit: 'hour', step: 1, format: "%h %a"});
                        }
                    }
                    break;
                case "month":
                    if (scaleInfo.cellUnit == 'day') {
                        switch (scaleInfo.cellPrecision) {
                            case "full":
                                scales.push({unit: 'hour', step: 24, format: "%D %d"});
                                break;
                            case "half":
                                scales.push({unit: 'day', step: 1, format: "%D %d"});
                                scales.push({unit: 'hour', step: 12, format: "%d %M %A"});
                                break;
                        }
                    }
                    if (scaleInfo.cellUnit == 'week') {
                        if (scaleInfo.cellPrecision == 'full') {
                            scales.push({unit: 'day', step: 7, format: "Week %W"});
                        }
                    }
                    break;
                case "year":
                    if (scaleInfo.cellUnit == 'week') {
                        if (scaleInfo.cellPrecision == 'full') {
                            scales.push({unit: 'day', step: 7, format: "Week %W"});
                        }
                    }
                    if (scaleInfo.cellUnit == 'month') {
                        if (scaleInfo.cellPrecision == 'full') {
                            scales.push({unit: 'month', step: 1, format: "%M %Y"});
                        }
                    }
                    break;
            }
            zoomLevels.push({
                name: scaleId,
                scales:scales,
            });
        }

        this.dhxGantt.ext.zoom.init({
            levels: zoomLevels
        });
    }

    _dhxDrag(startPoint, endPoint, startDate, endDate, tasksBetweenDates, tasksInRow) {
        const serializerFunc = this.useDateOnly ? serializeDate : serializeDateTime;
        let context = {};
        if (tasksInRow.length !== 0) {
            const task = tasksInRow[0];
            context = tasksInRow[0].context;

            const startDateStr = serializerFunc(DateTime.fromJSDate(this.dhxGantt.roundDate(startDate)));
            const endDateStr = serializerFunc(DateTime.fromJSDate(this.dhxGantt.roundDate(endDate)));

            context[sprintf('default_%s', this.model.dateStartField)] = startDateStr;
            context[sprintf('default_%s', this.model.dateStopField)] = endDateStr;

            this.props.openDialog({context: context});
        }
    }

    _dhxOnAfterTaskDrag(id, mode, e){
        const serializerFunc = this.useDateOnly ? serializeDate : serializeDateTime;
        const modes = this.dhxGantt.config.drag_mode;
        const task = this.dhxGantt.getTask(id);

        switch (mode) {
            case modes.move:
            case modes.resize:
                const startDate = serializerFunc(DateTime.fromJSDate(task.start_date));
                const endDate = serializerFunc(DateTime.fromJSDate(task.end_date));
                this.model.reschedule(task.record.id, startDate, endDate);
                break;
            case modes.progress:
                this.model.updateProgress(task.record.id, Math.round(task.progress * 1000 / 10));
                break;
        }
    }

    _dhxOnTaskClick(id, e){
        // since `click_drag` also trigger a click event, we arrive here when releasing the dragging
        // but we want to prevent to open form view of concerned task. This condition filters those
        // events.
        if (e.srcElement.classList.contains("gantt_task_row")) {
            return false;
        }

        const task = this.dhxGantt.getTask(id);
        if (task.record) {
            this.props.openDialog({resId: task.record.id});
        }
    }

    _dhxTaskClass(start, end, task){
        let classes = [];
        if (task.type == gantt.config.types.project) { // hide 'consolidate' group row
           classes.push("o_hidden");
        } else {
            const colorCode = task.color || 0;
            classes.push(sprintf("o_gantt_color_%s", colorCode));

            const evalContext = task.evalContext;
            for (const [decoration, expr] of Object.entries(this.decorationMap || {})) {
                const tokenExpr = py.parse(py.tokenize(expr));
                if (py.PY_isTrue(py.evaluate(tokenExpr, evalContext))) {
                    classes.push(decoration.replace('decoration-', 'o_gantt_decoration_'));
                }
            }
        }
        return classes.join(" ");
    }

}

GanttRenderer.template = "web_gantt.GanttRenderer";