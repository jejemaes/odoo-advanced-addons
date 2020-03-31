odoo.define('website_sale_rental.button_and_modal', function (require) {
    'use strict';

    var ajax = require('web.ajax');
    var core = require('web.core');
    var Dialog = require('web.Dialog');
    var Widget = require('web.Widget');
    var timeUtils = require('web.time');
    var session = require('web.session');

    var _t = core._t;
    var QWeb = core.qweb;
    var DATETIME_SERVER_FORMAT = "YYYY-MM-DD HH:mm:ss";


    var RentalButton = Widget.extend({
        events: {
            'click': '_onClick'
        },
        _onClick: function(ev) {
            var data = this.$el.data();
            if (data.rentalTracking == 'use_resource') {
                if (data.resourceCount === 1) {
                    this.modal = new RentalCalendarModal(this, {
                        productId: data.productId,
                        rentalTracking: data.rentalTracking,
                        rentalTenureMode: data.rentalTenureMode,
                        productRentalMinDuration: data.productRentalMinDuration,
                        timezone: data.rentalTimezone,
                        timezoneOffset: data.rentalTimezoneOffset,
                    });
                } else {
                    this.modal = new RentalModal(this, data);
                }
            } else {

            }
            this.modal.open();
        },
    });

    /**
     * Abstract Rental Modal
     *
     * This offers common part and behaviour to the other modals.
     */
    var AbstractRentalModal = Dialog.extend({
        xmlDependencies: Dialog.prototype.xmlDependencies.concat(
            ['/website_sale_rental/static/src/xml/website_sale_rental_modal.xml']
        ),
        init: function (parent, params) {
            var self = this;
            // modal set up
            var options = {
                title: _t("Configure Your Rental"),
                buttons: [
                    {'text': "Save", 'classes': 'btn-primary o_rental_modal_btn_save', 'click': this._onSave.bind(this)},
                    {'text': "Cancel", 'classes': 'btn-secondary', 'close': true},
                ],
                size: 'large',
            };
            this._super(parent, options);
            // modal ID
            this.modalId = _.uniqueId('rental-modal');
            // required to submit form and create a new Sales line
            this._requiredFields = ['datesUtc', 'quantityOrResourceIds', 'productId'];
            this._requiredFields.forEach(function(fname) {
                self.set(fname, false);
            });
            this.set('productId', params.productId);
            this.set('priceInfos', {});
            // timezone
            this.timezone = params.timezone;
            this.timezoneOffset = params.timezoneOffset;
        },
        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function() {
                self._requiredFields.forEach(function(fname) {
                    self.on('change:'+fname, self, self._onchangeRequiredFields);
                });
                self.on('change:priceInfos', self, self._onchangePriceInfos);
            });
        },
        set_buttons: function (buttons) {
            this._super.apply(this, arguments);
            this.$footer.wrapInner('<div class="p-2"></div>');
            this.$footer.append(QWeb.render('website_sale_rental.ModalFooterPrice', {widget: this}));
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        _addOrderLine: function () {
            var startUtc = this.get('datesUtc')[0];
            var stopUtc = this.get('datesUtc')[1];
            var qty = this.get('quantityOrResourceIds');
            if (_.isArray(qty)) {
                qty = qty.length;
            }
            return this._rpc({
                route: '/shop/cart/rental_add/',
                params: {
                    'product_id': this.get('productId'),
                    'start': startUtc,
                    'stop': stopUtc,
                    'qty': qty,
                    'resource_ids': this.get('quantityOrResourceIds'),
                }
            });
        },
        _canSave: function () {
            var self = this;
            return _.every(this._requiredFields, function(fname) { return !!self.get(fname); });
        },
        /**
         * Get rental calendar unavailabilities, for the current period.
         **/
        _fetchRentalCalendar: function (startUtc, stopUtc) {
            return this._rpc({
                route: '/website_sale_rental/'+this.get('productId')+'/calendar',
                params: {
                    'start': startUtc,
                    'stop': stopUtc,
                },
            });
        },
        /**
         * Get unavailabilites and rental bookings for all resources of the product, for the current period.
         **/
        _fetchResourcesCalendar: function (startUtc, stopUtc) {
            return this._rpc({
                route: '/website_sale_rental/'+this.get('productId')+'/resources',
                params: {
                    'start': startUtc,
                    'stop': stopUtc,
                },
            });
        },
        /**
         * Get the price simulation of the current product for the current period.
         **/
        _fetchSimulatePrice: function () {
            var startUtc = this.get('datesUtc')[0];
            var stopUtc = this.get('datesUtc')[1];
            if (startUtc < stopUtc) {
                var qty = this.get('quantityOrResourceIds');
                if (_.isArray(qty)) {
                    qty = qty.length;
                }
                return this._rpc({
                    route: '/website_sale_rental/'+this.get('productId')+'/simulate_price',
                    params: {
                        'start': startUtc,
                        'stop': stopUtc,
                        'qty_or_res_ids': this.get('quantityOrResourceIds'),
                    }
                });
            }
            return $.when();
        },

        _onchangePriceInfos: function () {
            this.$footer.find('.o_rental_modal_footer_price').replaceWith(QWeb.render('website_sale_rental.ModalFooterPrice', {widget: this}));
        },
        _onchangeRequiredFields: function() {
            var self = this;
            var canSave = this._canSave();

            var $btn = self.$footer.find('.o_rental_modal_btn_save');
            if(canSave) {
                $btn.removeClass('disabled');
            } else {
                $btn.addClass('disabled');
            }
            if (canSave) {
                this._fetchSimulatePrice().then(function(data) {
                    if (data) {
                        self.set('priceInfos', data);
                    }
                });
            } else {
                this.set('priceInfos', {});
            }
        },
        _strToUtcMoment: function (dateStr) {
            return moment.utc(timeUtils.str_to_datetime(dateStr));
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        _onSave: function (ev) {
            var self = this;
            if (this._canSave()) {
                this._addOrderLine().then(function (res) {
                    window.location.href = res['url'];
                });
            }
        },
    });

    /**
     * Widget for the Rental Calendar Modal
     *
     * Can only be used when only one resource is attached to the product (tracked with resource)
     */
    var RentalCalendarModal = AbstractRentalModal.extend({
        template: 'website_sale_rental.CalendarModal',

        init: function (parent, params) {
            this._super.apply(this, arguments);

            // business params
            this.resourceId = false;
            this.rentalTracking = params.rentalTracking;
            this.rentalTenureMode = params.rentalTenureMode;
            this.productRentalMinDuration = params.productRentalMinDuration;

            // calendar selector
            this._calendarSelector = 'rental-calendar-' + this.modalId;
            this.calendarDayMode = _.contains(['year', 'month', 'week', 'day'], this.productRentalMinDuration);
        },
        start: function () {
            var self = this;
            var res = $.when(this._super.apply(this, arguments)).then(function () {
                // resource
                //self.resourceId = initData['resource_ids'][0];

                self.$modal.on('shown.bs.modal', function(ev) {
                    var calendarEl = document.getElementById(self._calendarSelector);
                    var calendar = new FullCalendar.Calendar(calendarEl, self._getCalendarConfig());
                    calendar.render();
                });
            });
            return res;
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        _getCalendarConfig: function () {
            var self = this;

            var allowedViews = [];
            if (_.contains(['year', 'month', 'week', 'day'], this.productRentalMinDuration)) {
                allowedViews.push('dayGridMonth');
            }
            if (_.contains(['hour', 'minute'], this.productRentalMinDuration)) {
                allowedViews.push('timeGridWeek');
                allowedViews.push('timeGridDay');
            }

            return {
                plugins: ['interaction', 'dayGrid', 'timeGrid'],
                header: {
                    left: 'prev,next today',
                    center: 'title',
                    right: allowedViews.join(','),
                },
                timeZone: self.timezone,
                defaultDate: moment().format(DATETIME_SERVER_FORMAT),
                navLinks: true, // can click day/week names to navigate views
                selectable: true,
                firstDay: _t.database.parameters.week_start,
                validRange: {
                    start: moment().startOf('month').format("YYYY-MM-DD"),
                },
                select: function(info) {
                    var startDate = moment.utc(info.start).add(info.start.getTimezoneOffset(), 'minutes');
                    var endDate = moment.utc(info.end).add(info.end.getTimezoneOffset(), 'minutes');
                    var start = startDate.format(DATETIME_SERVER_FORMAT);
                    var end = endDate.format(DATETIME_SERVER_FORMAT);
                    self.set('datesUtc', [start, end]);
                },
                selectAllow: function(info) {
                    return info.start > moment();  // past days are not selectable
                },
                unselectAuto: false, // the selection stays when clicking outside
                selectOverlap: function (event) {
                    return false;
                },
                events: function(info, successCallback, failureCallback) {
                    var startDate = moment.utc(info.start).add(info.start.getTimezoneOffset(), 'minutes');
                    var endDate = moment.utc(info.end).add(info.end.getTimezoneOffset(), 'minutes');
                    var start = startDate.format(DATETIME_SERVER_FORMAT);
                    var end = endDate.format(DATETIME_SERVER_FORMAT);
                    self._fetchResourcesCalendar(start, end).then(function (data) {
                        var resourceId = _.keys(data['unavailabilities'])[0];

                        // required fields to save form: will trigger the disabling of the save btn
                        self.set('quantityOrResourceIds', [parseInt(resourceId)]);

                        var unavailabilities = self._unavailabilitiesToCalendarEvent(data['unavailabilities'][resourceId]);
                        var rental = self._rentalToCalendarEvent(data['rental'][resourceId]);
                        var intervals = rental.concat(unavailabilities);
                        successCallback(intervals);
                    });
                },
            };
        },
        _fetchSetUp: function () {
            return this._rpc({
                route: '/website_sale_rental/calendar_setup/'+this.get('productId'),
            });
        },
        _unavailabilitiesToCalendarEvent: function(data) {
            var self = this;
            var result = [];
            data.forEach(function(item){
                // convert into resource tz
                var start = self._strToUtcMoment(item[0]).subtract(self.timezoneOffset, 'minutes');
                var stop = self._strToUtcMoment(item[1]).subtract(self.timezoneOffset, 'minutes');
                // create the event
                var values = {
                    'start': start.format(DATETIME_SERVER_FORMAT),
                    'end': stop.format(DATETIME_SERVER_FORMAT),
                    'rendering': 'background',
                    'backgroundColor': 'grey',
                    'allDay': true,
                };
                result.push(values);
            });
            return result;
        },
        _rentalToCalendarEvent: function(data) {
            var self = this;
            var result = [];
            data.forEach(function(item){
                // convert into resource tz
                var start = self._strToUtcMoment(item[0]).subtract(self.timezoneOffset, 'minutes');
                var stop = self._strToUtcMoment(item[1]).subtract(self.timezoneOffset, 'minutes');
                // create the event
                var values = {
                    'start': start.format(DATETIME_SERVER_FORMAT),
                    'end': stop.format(DATETIME_SERVER_FORMAT),
                    'allDay': false,
                    'backgroundColor': item[2] ? 'red' : 'orange',
                    'classNames': item[2] ? ['o_rental_event_confirmed'] : ['o_rental_event_drafts'],
                };
                result.push(values);
            });
            return result;
        },
    });


    /**
     * Widget for the Rental Modal
     *
     * TO DO : this is not working !!
     */
    var RentalModal = Dialog.extend({
        xmlDependencies: Dialog.prototype.xmlDependencies.concat(
            ['/website_sale_rental/static/src/xml/website_sale_rental_modal.xml']
        ),
        template: 'website_sale_rental.Modal',

        init: function (parent, params) {
            // modal set up
            var options = {
                title: _t("Configure Your Rental"),
                buttons: [
                    {'text': "Save", 'classes': 'btn-primary'},
                    {'text': "Cancel", 'classes': 'btn-secondary', 'close': true},
                ],
                size: 'large',
            };
            this._super(parent, options);

            // business params
            this.productId = params.productId;
            this.rentalTracking = params.rentalTracking;
            this.rentalTenureMode = params.rentalTenureMode;
            this.initialResourceIds = params.resourceIds || [];

            this.set('start_dt_utc', false);
            this.set('stop_dt_utc', false);
            this.set('resources', []);
        },
        start: function () {
            var self = this;
            var res = this._super.apply(this, arguments).then(function () {
                // changing dates
                self.on('change:start_dt_utc', self, self._onchangeDates);
                self.on('change:stop_dt_utc', self, self._onchangeDates);
                self.on('change:resources', self, self._onchangeResources);
                // datepickers
                self.$('#datetimepicker-start').datetimepicker({
                    format: self.rentalTenureMode === 'day' ? 'L' : false,
                    widgetPositioning: {
                        horizontal: 'auto',
                        vertical: 'bottom'
                    },
                    minDate: moment(),
                });
                self.$('#datetimepicker-stop').datetimepicker({
                    format: self.rentalTenureMode === 'day' ? 'L' : false,
                    widgetPositioning: {
                        horizontal: 'auto',
                        vertical: 'bottom'
                    },
                    useCurrent: false,
                });
                self.$("#datetimepicker-start").on("change.datetimepicker", function (e) {
                    self.$('#datetimepicker-stop').datetimepicker('minDate', e.date);
                    if (e.date) {
                        self.set('start_dt_utc', e.date.utc());
                    }
                });
                self.$("#datetimepicker-stop").on("change.datetimepicker", function (e) {
                    self.$('#datetimepicker-start').datetimepicker('maxDate', e.date);
                    if (e.date) {
                        self.set('stop_dt_utc', e.date.utc());
                    }
                });
            });
            return res;
        },
        _fetchIsAvailable: function (start, stop) {
            start = timeUtils.datetime_to_str(start.toDate());
            stop = timeUtils.datetime_to_str(stop.toDate());
            return this._rpc({
                route: '/website_sale_rental/is_available',
                params: {
                    'product_id': this.productId,
                    'date_start': start,
                    'date_stop': stop,
                },
            });
        },
        _fetchUnavailabilities: function (start, stop) {
            start = timeUtils.datetime_to_str(start.toDate());
            stop = timeUtils.datetime_to_str(stop.toDate());
            return this._rpc({
                route: '/website_sale_rental/get_unavailabilities',
                params: {
                    'product_id': this.productId,
                    'date_start': start,
                    'date_stop': stop,
                },
            });
        },
        _onchangeDates: function() {
            var self = this;
            var start = this.get('start_dt_utc');
            var stop = this.get('stop_dt_utc');
            if (this.rentalTracking === 'use_resource') {
                if (start && stop) {
                    this._fetchIsAvailable(start, stop).then(function(data) {
                        self.set('resources', data);
                    });
                } else {
                    this.set('resources', []);
                }
            }
        },
        _onchangeResources: function() {
            self.$('.o_rental_form_resources').replaceWith(QWeb.render('website_sale_rental.Modal.resources', {'widget': this}));
        },
    });


    return {
        RentalModal: RentalModal,
        RentalButton: RentalButton,
    };

});
