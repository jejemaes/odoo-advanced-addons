odoo.define('web_view_gantt.GanttController', function (require) {
"use strict";

var AbstractController = require('web.AbstractController');
var GanttUtils = require('web_view_gantt.GanttUtils');
var core = require('web.core');
var config = require('web.config');
var Dialog = require('web.Dialog');
var dialogs = require('web.view_dialogs');
var time = require('web.time');

var _t = core._t;
var qweb = core.qweb;


var GanttController = AbstractController.extend({
    events: {
       // 'click .gantt_task_line': function(ev) { console.log('yolo', ev); }
    },
    custom_events: _.extend({}, AbstractController.prototype.custom_events, {
        drag_task: '_onTaskDragged',
        open_task: '_onTaskOpened',
        update_task_dates: '_onTaskDatesChanged',
        update_task_progress: '_onTaskProgressChanged',
    }),

    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);
        this.set('title', this.displayName);

        this.model = model;
        this.context = params.context;
        this.cellPrecisions = params.cellPrecisions;
        this.canPlan = params.canPlan;
        this.SCALES = params.SCALES;
        this.useDateOnly = params.useDateOnly;
        this.allowedScales = params.allowedScales;
        this.dialogViews = params.dialogViews;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @returns {string}
     */
    getTitle: function () {
        var state = this.model.get();
        var startDate = state.startDate;

        var subtitle = false;
        switch (state.scale) {
            case 'day':
                subtitle = state.startDate.format('L')
                break;
            case 'week':
                subtitle = state.startDate.format('LL')
                break;
            case 'month':
                subtitle = state.startDate.format('MMMM YYYY')
                break;
            case 'year':
                subtitle = state.startDate.format('[Year] YYYY')
                break;
        }
        return this._title + ' (' + subtitle + ')';
    },
    /**
     * Render the buttons according to the GanttView.buttons template and add
     * listeners on it. Set this.$buttons with the produced jQuery element
     *
     * @param {jQuery} [$node] a jQuery node where the rendered buttons should
     *   be inserted $node may be undefined, in which case they are inserted
     *   into this.options.$buttons
     */
    renderButtons: function ($node) {
        var self = this;
        if (!$node) {
            var state = this.model.get();
            this.$buttons = $(qweb.render('GanttView.buttons', {
                groupedBy: state.groupedBy,
                widget: this,
                SCALES: this.SCALES,
                activateScale: state.scale,
                allowedScales: this.allowedScales,
                isMobile: config.device.isMobile,
            }));
            this.$buttons.appendTo($node);

            this.$buttons.find('.o_gantt_button_add').bind('click', function (event) {
                return self._onAddClicked(event);
            });
            this.$buttons.find('.o_gantt_button_scale').bind('click', function (event) {
                return self._onScaleClicked(event);
            });

            this.$buttons.find('.o_gantt_button_prev').bind('click', function (event) {
                return self._onPrevPeriodClicked(event);
            });
            this.$buttons.find('.o_gantt_button_next').bind('click', function (event) {
                return self._onNextPeriodClicked(event);
            });
            this.$buttons.find('.o_gantt_button_today').bind('click', function (event) {
                self.model.setFocusDate(moment(new Date()));
                return self.reload();
            });
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Open the form view modal, but set default dates before in context.
     *
     * @private
     * @param {Object}  task
     * @param {boolean} [readonly=false]
     */
    _onCreateAction: function(context) {
        var context = context || {};
        var state = this.model.get();

        var startContextKey = 'default_' + state.dateStartField;
        var stopContextKey = 'default_' + state.dateStopField;
        if (!(startContextKey in context)) {
            context[startContextKey] = GanttUtils.dateToServer(state.focusDate.clone().startOf(state.scale), this.useDateOnly);
        }
        if (!(stopContextKey in context)) {
            context[stopContextKey] = GanttUtils.dateToServer(state.focusDate.clone().endOf(state.scale), this.useDateOnly);
        }
        this._openFormDialog(false, context);
    },
    /**
     * Opens dialog to add/edit/view a record
     *
     * @private
     * @param {integer|undefined} resID
     * @param {Object|undefined} context
     */
    _openFormDialog: function (resID, context) {
        var title = resID ? _t("Open") : _t("Create");

        var dialog = new dialogs.FormViewDialog(this, {
            title: _.str.sprintf(title),
            res_model: this.modelName,
            view_id: this.dialogViews[0][0],
            res_id: resID,
            readonly: !this.is_action_enabled('edit'),
            deletable: this.is_action_enabled('edit') && resID,
            context: _.extend({}, this.context, context),
            on_saved: this.reload.bind(this, {}),
            on_remove: this._openDeleteDialog.bind(this, resID),
        }).open();
        return dialog;
    },
    /**
     * Handler called when clicking the
     * delete button in the edit/view dialog.
     * Reload the view and close the dialog
     *
     * @returns {function}
     */
    _openDeleteDialog: function (resID) {
        var controller = this;

        var confirm = new Promise(function (resolve) {
            Dialog.confirm(this, _t('Are you sure to delete this record?'), {
                confirm_callback: function () {
                    resolve(true);
                },
                cancel_callback: function () {
                    resolve(false);
                },
            });
        });

        return confirm.then(function (confirmed) {
            if ((!confirmed)) {
                return Promise.resolve();
            }
            return controller._rpc({
                model: controller.modelName,
                method: 'unlink',
                args: [[resID,],],
            }).then(function () {
                return controller.reload();
            })
        });
    },
     /**
     * Opens dialog to plan records.
     *
     * @private
     * @param {Object} context
     */
    _openPlanDialog: function (dateValues, context) {
        var self = this;
        var state = this.model.get();
        var domain = ['|', [state.dateStartField, '=', false], [state.dateStopField, '=', false]];
        return new dialogs.SelectCreateDialog(this, {
            title: _t("Plan"),
            res_model: this.modelName,
            domain: this.model.domain.concat(domain),
            views: this.dialogViews,
            context: _.extend({}, this.context, context),
            on_selected: function (records) {
                var ids = _.pluck(records, 'id');
                if (ids.length) {
                    // Here, the dates are already in server time so we set the
                    // isUTC parameter of reschedule to true to avoid conversion
                    self._reschedule(ids, dateValues);
                }
            },
        }).open();
    },
    /**
     * @private
     * @param {Moment} focusDate
     */
    _focusDate: function (focusDate) {
        var self = this;
        this.model.setFocusDate(focusDate);
        this.reload();
    },
    /**
     * @private
     * @param {any} scale
     */
    _setScale: function (scale) {
        var self = this;

        this.model.setScale(scale);
        this.reload();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onAddClicked: function (ev) {
        ev.preventDefault();
        return this._onCreateAction();
    },
    /**
     * Gantt row has been drag'n'drop or expand. The related task should be rescheduled.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onTaskDatesChanged: function (ev) {
        var self = this;
        var state = this.model.get();
        var recordIds = ev.data.resId;
        var startDate = ev.data.start;
        var stopDate = ev.data.stop;
        return this.model.reschedule(recordIds, _.object([state.dateStartField, state.dateStopField], [startDate, stopDate])).guardedCatch(function(ev){
            self.reload();
        });
    },
    /**
     * Gantt row has been dragged on the timeline.
     *
     * @private
     * @param {OdooEvent} ev
     **/
    _onTaskDragged: function (ev) {
        var state = this.model.get();
        var values = ev.data.values || {};

        values[state.dateStartField] = GanttUtils.dateToServer(ev.data.dates[0], this.useDateOnly);
        values[state.dateStopField] = GanttUtils.dateToServer(ev.data.dates[1], this.useDateOnly);

        var context = {};
        for (var k in values) {
            context[_.str.sprintf('default_%s', k)] = values[k];
        }

        if (this.canPlan) {
            return this._openPlanDialog(values);
        }
        return this._onCreateAction(context);
    },
    /**
     * Gantt row has been dragged on the timeline.
     *
     * @private
     * @param {OdooEvent} ev
     **/
    _onTaskOpened: function (ev) {
        return this._openFormDialog(ev.data.resId);
    },
    /**
     * Gantt row progress has been dragged.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onTaskProgressChanged: function (ev) {
        var progress = ev.data.progress || 0.0;
        var ids = ev.data.resId;
        this.model.changeProgress(ids, progress);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onNextPeriodClicked: function (ev) {
        ev.preventDefault();
        var state = this.model.get();
        this.update({ date: state.focusDate.add(1, state.scale) });
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onPrevPeriodClicked: function (ev) {
        ev.preventDefault();
        var state = this.model.get();
        this.update({ date: state.focusDate.subtract(1, state.scale) });
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onScaleClicked: function (ev) {
        ev.preventDefault();
        var $button = $(ev.currentTarget);
        this.$buttons.find('.o_gantt_button_scale').removeClass('active');
        $button.addClass('active');
        this.$buttons.find('.o_gantt_dropdown_selected_scale').text($button.text()); // TODO JEM: required ?
        this.update({ scale: $button.data('value') });
    },
});

return GanttController;

});
