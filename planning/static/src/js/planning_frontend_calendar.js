/* eslint-disable no-undef */
odoo.define('planning.calendar_frontend', function (require) {
"use strict";

const publicWidget = require('web.public.widget');

publicWidget.registry.PlanningView = publicWidget.Widget.extend({
    selector: '#o_planning_widget',
    jsLibs: [
        '/web/static/lib/fullcalendar/core/main.js',
        '/web/static/lib/fullcalendar/core/locales-all.js',
        '/web/static/lib/fullcalendar/interaction/main.js',
        '/web/static/lib/fullcalendar/moment/main.js',
        '/web/static/lib/fullcalendar/daygrid/main.js',
        '/web/static/lib/fullcalendar/timegrid/main.js',
        '/web/static/lib/fullcalendar/list/main.js'
    ],
    cssLibs: [
        '/web/static/lib/fullcalendar/core/main.css',
        '/web/static/lib/fullcalendar/daygrid/main.css',
        '/web/static/lib/fullcalendar/timegrid/main.css',
        '/web/static/lib/fullcalendar/list/main.css'
    ],
    events: {
        'click .o_planning_collaborative_btn': '_onClickCollaborativeBtn',
        'change #collaborativeEmployee': '_onChangeCollaborativeEmployee',
    },
    start: function () {
        this._super.apply(this, arguments);
        this.calendarElement = this.$(".o_calendar_widget")[0];
        this.modalElement = this.$("#o_planning_calendar_modal");
        this.openshiftTableElement = this.$('.o_planning_openshift_table');
        this.planningToken = this.$el.data('planning-token');

        const data = window.planning_calendar_data || {};
        const assignedShifts = this._toCalendarEvent(data.assigned_shifts_data || []);

        // assigned shift calendar
        if (this.calendarElement && assignedShifts) {
            const minTime = moment.utc(data.planning_min_dt);
            const maxTime = moment.utc(data.planning_max_dt);
            const locale = data.locale || "en";
            const defaultStart = moment.utc(data.planning_min_dt).toDate();
            const defaultView ='dayGridMonth';
            let titleFormat = 'MMMM YYYY';
            let calendarHeaders = {
                left: 'dayGridMonth,dayGridWeek,timeGrid,listMonth',
                center: 'title',
                right: 'today,prev,next'
            };

           this.calendar = new FullCalendar.Calendar(this.calendarElement, {
                // Settings
                plugins: [
                    'moment',
                    'dayGrid',
                    'timeGrid',
                    'list',
                    'interraction',
                    'momentTimezone'
                ],
                timeZone: 'local',
                locale: locale,
                defaultView: defaultView,
                navLinks: true, // can click day/week names to navigate views
                eventLimit: true, // allow "more" link when too many events
                titleFormat: titleFormat,
                defaultDate: defaultStart,
                timeFormat: 'LT',
                displayEventEnd: true,
                height: 'auto',
                eventTextColor: 'white',
                eventOverlap: true,
                eventTimeFormat: {
                    hour: 'numeric',
                    minute: '2-digit',
                    meridiem: 'long',
                    omitZeroMinute: true,
                },
                validRange: { // does not work
                    start: minTime,
                    end: maxTime
                },
                header: calendarHeaders,
                // Data
                events: assignedShifts,
                // Event Function is called when clicking on the event
                eventClick: _.bind(this._onclickEvent, this),
                // views
                views: {
                    timeGrid: {
                       buttonText: 'day'
                    },
                },
            });
            this.calendar.render();

        }
        // update dates (convert UTC data attribute into browser timezone)
        let now = new Date();
        this.$('.o_planning_autochange_date').each(function(index, elem){
            let date = moment.utc(elem.dataset.date);
            let dateFormat = elem.dataset.format || 'LLLL';
            date = date.add(-now.getTimezoneOffset(), 'minutes');
            $(elem).text(date.format(dateFormat));
        });
    },
    _toCalendarEvent (data) {
        var self = this;
        var result = [];
        data.forEach(function(item){
            // create the  fullcalendar event
            var values = {
                'title': item.title,
                'start': moment.utc(item.start_utc).format(),
                'end': moment.utc(item.end_utc).format(),
                'backgroundColor': item.color,
                'initial_data': item,
            };
            result.push(values);
        });
        return result;
    },
    _onclickEvent: function (calEvent) {
        let data = calEvent.event.extendedProps.initial_data;
        this._displayModal(data);
    },
    _displayModal: function(shiftData){
        let now = new Date();
        let start_date = moment.utc(shiftData.start_utc).add(-now.getTimezoneOffset(), 'minutes');
        let end_date = moment.utc(shiftData.end_utc).add(-now.getTimezoneOffset(), 'minutes');

        this.modalElement.find(".modal-title").text(shiftData.title);
        this.modalElement.find(".modal-header").css("background-color", shiftData.color);
        this.modalElement.find("#start").text(start_date.format("YYYY-MM-DD hh:mm A"));
        this.modalElement.find("#stop").text(end_date.format("YYYY-MM-DD hh:mm A"));
        this.modalElement.find("#role_name").text(shiftData.role_description || '');
        this.modalElement.find("#note").text(shiftData.note || '');

        // collaborative assignement
        let collaborativeUrl = shiftData.collaborative_employee_url;
        if (!shiftData.employee_name) {
            if (collaborativeUrl) {
                this.modalElement.find("#employee").text('');
                this.modalElement.find('.o_planning_collaborative_employee').show();
                this.modalElement.find('#modal_form_collaborative_assign').show()
                this.modalElement.find('#modal_form_collaborative_unassign').hide()

                $('#collaborativeEmployee').select2({
                    placeholder: 'Select an option',
                    theme: "bootstrap",
                    dropdownParent: $('#modal_form_collaborative_assign'),
                    ajax: {
                        url: collaborativeUrl,
                        dataType: 'json',
                        data: function (term) {
                            return {
                                query: term,
                                limit: 50,
                            };
                        },
                        results: function (data) {
                            var ret = [];
                            _.each(data, function (x) {
                                ret.push({
                                    id: x.id,
                                    text: x.display_name,
                                });
                            });
                            return {results: ret};
                        },
                    }
                });
            }
        } else {
            if (collaborativeUrl) {
                this.modalElement.find("#employee").text(shiftData.employee_name || '');
                this.modalElement.find('.o_planning_collaborative_employee').hide();
                this.modalElement.find('#modal_form_collaborative_assign').hide();
                this.modalElement.find('#modal_form_collaborative_unassign').show();
            }
        }
        this.modalElement.find('#modal_form_collaborative_assign button').addClass('disabled');
        this.modalElement.find('input[name="shift_id"]').val(shiftData.id); // both collaborative form

        // unassign
        if (shiftData.can_self_unassign) {
            this.modalElement.find('#modal_form_dismiss_shift').show()
            this.modalElement.find('#modal_form_dismiss_shift').attr('action', shiftData.can_self_unassign_url);
        } else {
            this.modalElement.find('#modal_form_dismiss_shift').hide()
            this.modalElement.find('#modal_form_dismiss_shift').attr('action', '');
        }
        this.modalElement.modal("show");
    },
    _onClickCollaborativeBtn: function(ev){
        let shiftData = $(ev.currentTarget).data('shift-data');
        this._displayModal(shiftData);
    },
    _onChangeCollaborativeEmployee: function(ev){
        let value = $(ev.currentTarget).val();
        if (value) {
            this.modalElement.find('#modal_form_collaborative_assign input[name="employee_id"]').val(value);
            this.modalElement.find('#modal_form_collaborative_assign button').removeClass('disabled');
        }
    },
});

// Add client actions
return publicWidget.registry.PlanningView;
});
