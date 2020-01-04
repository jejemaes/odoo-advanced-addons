odoo.define('web_view_gantt.GanttRenderer', function (require) {
"use strict";

var AbstractRenderer = require('web.AbstractRenderer');
var core = require('web.core');
var field_utils = require('web.field_utils');
var time = require('web.time');
var qweb = require('web.QWeb');
var session = require('web.session');
var utils = require('web.utils');

var _lt = core._lt;
var QWeb = core.qweb;

return AbstractRenderer.extend({
    className: "o_gantt_view",
    events: {
        'click .gantt_task_line': '_onTaskClick',
    },

    /**
     * @overrie
     */
    init: function (parent, state, params) {
        var self = this;
        this._super.apply(this, arguments);

        this.fieldsInfo = params.fieldsInfo;
        this.SCALES = params.SCALES;
        this.string = params.string;
        this.canCreate = params.canCreate;
        this.canEdit = params.canEdit;
        this.canPlan = params.canPlan;
        this.cellPrecisions = params.cellPrecisions;
        this.colorField = params.colorField;
        this.progressField = params.progressField;
        // this.collapseFirstLevel = params.collapseFirstLevel;
        // this.thumbnails = params.thumbnails;

        // unique identifier for the dhtmlxgantt lib
        this.dhx_id = _.uniqueId('dhx_');
        // events bound on lib
        this.dhx_events = [];
        // the global gantt instance
        this.dhx_gantt = gantt;
    },
    /**
     * @override
     */
    destroy: function () {
        while (this.dhx_events.length) {
            gantt.detachEvent(this.dhx_events.pop());
        }
        this._super();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _ganttBindEvents: function () {
        var self = this;
        // prevent ligthbox on double click
        this.dhx_events.push(gantt.attachEvent("onTaskDblClick", function(id, e){
            return false; // prevent lightbox to open
        }));
        // allow edit
        this.dhx_events.push(gantt.attachEvent("onAfterTaskDrag", function(id, mode, e){
            var row = self.dhx_gantt.getTask(id);
            if (_.contains(['resize', 'move'], mode)) {
                self.trigger_up('update_task_dates', {
                    'resId': row.id,
                    'start': moment(row.start_date),
                    'stop': moment(row.end_date),
                });
                return false; // prevent lightbox to open
            }
            if (mode === 'progress') {
                self.trigger_up('update_task_progress', {
                    'resId': row.id,
                    'progress': row.progress * 100,
                });
            }
        }));
    },

    _ganttConfig: function() {
        var self = this;
        // time format
        this.dhx_gantt.config.xml_date = "%Y-%m-%d %H:%i:%s";
        this.dhx_gantt.config.date_format = "%Y-%m-%d %H:%i:%s";
        this.dhx_gantt.config.duration_unit = "minute";
        this.dhx_gantt.config.duration_step = 60;

        // ui
        this.dhx_gantt.config.scale_height = 75;
        this.dhx_gantt.config.autosize = "y";
        this.dhx_gantt.config.columns = [{
            name: "text",
            label: _lt("Gantt View"),
            tree: true,
            width: '*',
            resize: true,
        }];
        this.dhx_gantt.config.initial_scroll = false;
        this.dhx_gantt.config.preserve_scroll = true;
        this.dhx_gantt.config.show_progress = !!this.progressField;

        // drag options
        this.dhx_gantt.config.drag_resize = this.canEdit; // allow resize gantt task
        this.dhx_gantt.config.drag_move = this.canEdit; // allow moving gantt task
        this.dhx_gantt.config.drag_progress = !!this.progressField && this.canEdit && !this.fieldsInfo[this.progressField].readonly; // allow changing progress
        this.dhx_gantt.config.drag_links = false;
        if (this.canCreate || this.canPlan) {
            this.dhx_gantt.config.click_drag = {
                callback: _.bind(this._ganttDrag, this),
                singleRow: true
            };
        }

        // scales
        this.dhx_gantt.config.start_on_monday = moment().startOf("week").day();
        this.dhx_gantt.config.scales = this._ganttGetScales();
        this.dhx_gantt.config.start_date = this.state.startDate;
        this.dhx_gantt.config.end_date = this.state.stopDate;

        // templates
        this.dhx_gantt.templates.timeline_cell_class = function(row, date){
            var classes = '';
            // style for today cell column
            var today = new Date();
            if (self.state.scale !== "day" && date.getDate() === today.getDate() && date.getMonth() === today.getMonth() && date.getYear() === today.getYear()) {
                classes += " o_today";
            }
            return classes;
        };
        this.dhx_gantt.templates.progress_text = function(start, end, task){
            if (self.dhx_gantt.config.show_progress) {
                return _.str.sprintf('%s %%', Math.round(task.progress * 10) / 10);
            }
            return '';
        };
        this.dhx_gantt.templates.task_class = function(start, end, task){
            var classes = '';
            // hide 'consolidate' group row
            if (task.type === self.dhx_gantt.config.types.project) {
                classes += ' o_hidden';
            }
            return classes;
        };
    },

    _ganttDrag: function(startPoint, endPoint, startDate, endDate, tasksBetweenDates, tasksInRow) {
        var data;
        var currentTask;
        if (tasksInRow.length !== 0) {
            var currentTask = tasksInRow[0];
            data = currentTask.values;
        }
        console.log("drag ------  canPlan=", this.canPlan, data);
        this.trigger_up('drag_task', {
            dates: [moment(this.dhx_gantt.roundDate(startDate)), moment(this.dhx_gantt.roundDate(endDate))],
            values: data || {},
        });
        return false;
    },

    _ganttGetScales: function () {
        var scaleMainFormat = {
            day: "%D %d %M %Y",
            week: "Week #%W",
            month: "%F %Y",
            year: "%Y",
        };

        var scale = this.state.scale;
        var scaleInfo = this.cellPrecisions[this.state.scale];
        var result = [{unit: scale, step: 1, format: scaleMainFormat[scale]}];
        switch (scale) {
            case "day":
                if (scaleInfo.unit == 'hour') {
                    switch (scaleInfo.precision) {
                        case "full":
                            result.push({unit: 'minute', step: 60, format: "%h %a"});
                            break;
                        case "half":
                            result.push({unit: 'hour', step: 1, format: "%h %a"});
                            result.push({unit: 'minute', step: 30, format: "%i"});
                            break;
                        case "quarter":
                            result.push({unit: 'hour', step: 1, format: "%h %a"});
                            result.push({unit: 'minute', step: 15, format: "%i"});
                            break;
                    }
                }
                break;
            case "week":
                if (scaleInfo.unit == 'day') {
                    switch (scaleInfo.precision) {
                        case "full":
                            result.push({unit: 'hour', step: 24, format: "%D %d %M"});
                            break;
                        case "half":
                            result.push({unit: 'hour', step: 12, format: "%h %a"});
                            break;
                    }
                }
                if (scaleInfo.unit == 'hour') {
                    if (scaleInfo.precision == 'full') {
                        result.push({unit: 'day', step: 1, format: "%D %d %M"});
                        result.push({unit: 'hour', step: 1, format: "%h %a"});
                    }
                }
                break;
            case "month":
                if (scaleInfo.unit == 'day') {
                    switch (scaleInfo.precision) {
                        case "full":
                            result.push({unit: 'hour', step: 24, format: "%D %d"});
                            break;
                        case "half":
                            result.push({unit: 'day', step: 1, format: "%D %d"});
                            result.push({unit: 'hour', step: 12, format: "%d %M %A"});
                            break;
                    }
                }
                if (scaleInfo.unit == 'week') {
                    if (scaleInfo.precision == 'full') {
                        result.push({unit: 'day', step: 7, format: "Week %W"});
                    }
                }
                break;
            case "year":
                if (scaleInfo.unit == 'week') {
                    if (scaleInfo.precision == 'full') {
                        result.push({unit: 'day', step: 7, format: "Week %W"});
                    }
                }
                if (scaleInfo.unit == 'month') {
                    if (scaleInfo.precision == 'full') {
                        result.push({unit: 'month', step: 1, format: "%M %Y"});
                    }
                }
                break;
        }
        return result;
    },

    _ganttGetTaskList: function () {
        var tasks = this._ganttGenerateTask(this.state.rows);
        return tasks;
    },
    _ganttGenerateTask: function (rows) {
        var self = this;
        var tasks = [];
        rows.forEach(function(row) {
            if (row.rows) {
                tasks.push({
                    id: row.id,
                    text: row.name,
                    type: gantt.config.types.project,
                    open: true,
                    parent: row.parentId,
                    values: row.data,
                    // dummy field to avoid "invalid dates" error. No pill will be displayed.
                    //start_date: time.datetime_to_str(self.state.focusDate.toDate()),
                    duration: 0,
                });
                tasks = tasks.concat(self._ganttGenerateTask(row.rows));
            } else {
                (row.records || []).forEach(function(rec) {
                    var startDate = rec[self.state.dateStartField];
                    var stopDate = rec[self.state.dateStopField];

                    tasks.push({
                        id: rec.id,
                        text: rec.display_name,
                        start_date: time.datetime_to_str(startDate.toDate()),
                        duration: self.dhx_gantt.calculateDuration(startDate.toDate(), stopDate.toDate()),
                        type: gantt.config.types.task,
                        progress: rec[self.progressField] ? rec[self.progressField] / 100.0 : 0.0,
                        parent: row.parentId,
                        values: row.data,
                    });
                });
            }
        });
        return tasks;
    },
    _ganttPopulate: function () {
        this.dhx_gantt.clearAll();
        var data = {'data': this._ganttGetTaskList(), 'links': []};
        this.dhx_gantt.parse(data);
    },

    /**
     * @private
     * @returns {Deferred}
     */
    _render: function () {
        // horrible hack to make sure that something is in the dom with the required
        // id.  The problem is that the action manager renders the view in a document
        // fragment.
        var temp_div_with_id;
        if (this.$div_with_id){
            temp_div_with_id = this.$div_with_id;
        }
        var $container = $(QWeb.render('GanttView', {widget: this}));
        this.$div_with_id = $container.find('#' + this.dhx_id);
        this.$div_with_id.wrap('<div class="container-fluid p-0"></div>');
        this.$div = $container;
        this.$div.prependTo(document.body);

        // Initialize the gantt chart
        while (this.dhx_events.length) {
            this.dhx_gantt.detachEvent(this.dhx_events.pop());
        }

        this._ganttConfig();
        this._ganttBindEvents();
        this.dhx_gantt.init(this.dhx_id);
        this._ganttPopulate();

        // End of horrible hack
        var scroll_state = this.dhx_gantt.getScrollState();
        this.$el.empty();
        this.$el.append(this.$div.contents());
        this.dhx_gantt.scrollTo(scroll_state.x, scroll_state.y);
        this.$div.remove();
        if (temp_div_with_id) {
            temp_div_with_id.remove();
        }
        return $.when();
    },

    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------

    _onTaskClick: _.debounce(function (ev) {
        ev.preventDefault();
        var taskId = $(ev.currentTarget).attr("task_id");
        this.trigger_up('open_task', {resId: parseInt(taskId)});
        return false;
    }, 500, true),
});

});
