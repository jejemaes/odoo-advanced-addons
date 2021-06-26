odoo.define('website_sale_rental.rental_calendar', function (require) {
'use strict';

const core = require('web.core');
const dom = require('web.dom');
const publicWidget = require('web.public.widget');
const wUtils = require('website.utils');

const DATETIME_SERVER_FORMAT = "YYYY-MM-DD HH:mm:ss";

var _t = core._t;


function onVisible(element, callback) {
    new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if(entry.intersectionRatio > 0) {
                callback(element);
                observer.disconnect();
            }
        });
    }).observe(element);
}


publicWidget.registry.websiteSaleRentalButton = publicWidget.Widget.extend({
    selector: '.o_website_sale_rental_btn',
    events: {
        'click': '_onClick',
    },
    _onClick: function (ev) {
        ev.preventDefault();

        var classname = '.o_website_sale_rental_mode_' + this.$el.data('mode');
        dom.scrollTo($(classname)[0], {
            easing: 'linear',
            duration: 500,
        });
    },


});


publicWidget.registry.websiteSaleRentalCalendar = publicWidget.Widget.extend({
    selector: '.o_website_sale_rental_mode_calendar',
    custom_events: {
        'change_dates': '_onChangeDates',
    },
    /**
     * @override
     */
    async start() {
        var self = this;
        const rentalData = this.$el.data();
        return this._super.apply(this, arguments).then(function () {
            var bindSubWidgets = function(){
                self.form = new RentalForm(self, rentalData);
                self.form.attachTo(self.$('.o_website_sale_rental_js_form'));

                self.calendar = new RentalCalendar(self, rentalData);
                self.calendar.appendTo(self.$('.o_website_sale_rental_calendar_container')[0]);
            }
            onVisible(document.querySelector('.o_website_sale_rental_calendar_container'), bindSubWidgets);
        });
    },
    _onChangeDates (ev) {
        this.form.$startInput.datetimepicker('date', ev.data['startDate']);
        this.form.$stopInput.datetimepicker('date', ev.data['stopDate']);
    },
});


publicWidget.registry.websiteSaleRentalFormOnly = publicWidget.Widget.extend({
    selector: '.o_website_sale_rental_mode_form',

    /**
     * @override
     */
    async start() {
        var self = this;
        const rentalData = this.$el.data();
        return this._super.apply(this, arguments).then(function () {
            self.$el.on('shown.bs.collapse', function(){
                const form = new RentalForm(self, rentalData);
                form.attachTo(self.$('.o_website_sale_rental_js_form'));
            });
        });
    },
});


var RentalForm = publicWidget.Widget.extend({
    events: _.extend({}, publicWidget.Widget.prototype.events, {
        'change #rental-quantity': '_onChangeQty',
        'click .o_website_sale_rental_submit': '_onclickSubmit',
    }),

    init: function (parent, options) {
        this._super(...arguments);

        this.productTemplateId = options['productTemplateId'];
        this.productId = options['productId'];
        this.rentalMinDuration = options['rentalMinDuration'];
        this.rentalResourceCount = options['rentalResourceCount'];
        this.rentalResourceId = options['rentalResourceId'];

        // dates are store in server format (str) in utc
        this.set('startDateUtc', false);
        this.set('stopDateUtc', false);
        this.set('quantity', 1);

        this._recomputePrice = _.debounce(this._recomputePrice, 50);
    },
    /**
     * @override
     */
    async start(parent, options) {
        var self = this;
        return this._super(...arguments).then(function() {
            self.on('change:startDateUtc', self, self._recomputePrice);
            self.on('change:stopDateUtc', self, self._recomputePrice);
            self.on('change:quantity', self, self._recomputePrice);

            // ui elements
            self.$submitBtn = self.$('.o_website_sale_rental_submit');
            self.$startInput = self.$('#rental-datetimepicker-start');
            self.$stopInput = self.$("#rental-datetimepicker-stop");
            self.$priceInput = self.$('#rental-unitprice');
            self.$priceExplanation = self.$('.o_website_sale_rental_price_explanation');
            self.$error = self.$('.o_website_sale_rental_price_form_error');

            // setup date pickers
            self.$startInput.datetimepicker({'minDate': moment()});
            self.$startInput.on("change.datetimepicker", function (e) {
                self.$stopInput.datetimepicker('minDate', e.date);
                if (e.date) {
                    self.set('startDateUtc', e.date.utc().second(0).format(DATETIME_SERVER_FORMAT));
                }
                self.$stopInput.focus();
            });
            self.$stopInput.on("change.datetimepicker", function (e) {
                //self.$('#rental-datetimepicker-start').datetimepicker('maxDate', e.date);
                if (e.date) {
                    self.set('stopDateUtc', e.date.utc().second(0).format(DATETIME_SERVER_FORMAT));
                }
            });

        });
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    /**
     * Get the price simulation of the current product for the current period.
     **/
    _addSaleLine () {
        var start = this.get('startDateUtc');
        var stop = this.get('stopDateUtc');
        return wUtils.sendRequest('/shop/cart/update/',
            {
                'product_id': this.productId,
                'add_qty': this.get('quantity'),
                'rental_start': start,
                'rental_stop': stop,
                'is_rental': true,
            }
        );
    },
    _checkSubmitButton(hasError) {
        if (hasError) {
            this.$submitBtn.addClass('disabled');
        } else {
            var start = this.get('startDateUtc');
            var stop = this.get('stopDateUtc');
            var qty = this.get('quantity');
            if (start < stop && qty >= 1) {
                this.$submitBtn.removeClass('disabled');
            } else {
                this.$submitBtn.addClass('disabled');
            }
        }
    },
    /**
     * Get the price simulation of the current product for the current period.
     **/
    _fetchPrice (startUtc, stopUtc, qty) {
        return this._rpc({
            route: '/shop/rental/'+this.productTemplateId+'/price',
            params: {
                'start': startUtc,
                'stop': stopUtc,
                'qty': qty
            }
        });
    },
    _recomputePrice () {
        var self = this;
        var start = this.get('startDateUtc');
        var stop = this.get('stopDateUtc');
        var qty = this.get('quantity');
        this.$error.addClass('d-none');
        if (start && stop && qty) {
            this._fetchPrice(start, stop, qty).then(function(data) {
                self._setPrice(data);
                self._setError(data['error']);
                self._checkSubmitButton(!!data['error']);
            });
        }
    },
    _setPrice (data) {
        this.$priceExplanation.text(data['pricing_explanation']);
        this.$priceInput.val(data['price']);
    },
    _setError (msg) {
        if (msg) {
            this.$error.text(msg);
            this.$error.removeClass('d-none');
        }
    },
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------
    _onChangeQty (ev) {
        var qty = $(ev.currentTarget).val();
        this.set('quantity', parseInt(qty));
    },
    _onclickSubmit(ev) {
        this._addSaleLine();
    },
});


var RentalCalendar = publicWidget.Widget.extend({
    jsLibs: [
        '/web/static/lib/fullcalendar/core/main.js',
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

    xmlDependencies: ['/website_sale_rental/static/src/xml/website_sale_rental_modal.xml'],
    template: 'website_sale_rental.RentalCalendar',

    init: function (parent, options) {
        this.productTemplateId = options['productTemplateId'];
        this.rentalMinDuration = options['rentalMinDuration'];

        this.calendar = null;
        return this._super(...arguments);
    },
    /**
     * @override
     */
    async start(parent, options) {
        var self = this;
        return this._super(...arguments).then(function() {
            self._initCalendar();
            self.calendar.render();
        });
    },

    _initCalendar () {
        var $calendarElement = this.$el[0]; // first child of the template
        var locale = moment.locale();

        var fcOptions = this._getFullCalendarOptions({
            locale: locale, // reset locale when fullcalendar has already been instanciated before now
        });
        this.calendar = new FullCalendar.Calendar($calendarElement, fcOptions);
    },

    /**
     * Return the Object options for FullCalendar
     *
     * @private
     * @param {Object} fcOptions
     * @return {Object}
     */
    _getFullCalendarOptions (fcOptions) {
        var self = this;

        var allowedViews = ['dayGridMonth', 'timeGridWeek', 'timeGridDay'];
        var defaultView = 'timeGridWeek';
        if (self.rentalMinDuration && _.contains(['day', 'week', 'month'], self.rentalMinDuration)) {
            defaultView = 'dayGridMonth';
        }

        return {
            plugins: ['interaction', 'dayGrid', 'timeGrid', 'dayGrid', 'momentTimezone'],
            header: {
                left: 'prev,next today',
                center: 'title',
                right: allowedViews.join(','),
            },
            defaultView: defaultView,
           // timeZone: this.rentalTimezone,
            defaultDate: moment().format("YYYY-MM-DD"),
            navLinks: true, // can click day/week names to navigate views
            selectable: true,
            firstDay: _t.database.parameters.week_start,
            validRange: {
                start: moment.utc().startOf('month').format("YYYY-MM-DD"),
            },
            select: function(info) {
                var startUtc =  moment(info.start).add(info.start.getTimezoneOffset(), 'minutes');
                var stopUtc =  moment(info.end).add(info.end.getTimezoneOffset(), 'minutes');

                self.trigger_up('change_dates', {
                    'startDateUtc': startUtc,
                    'stopDateUtc': stopUtc,
                    'startDate': moment(info.start),
                    'stopDate': moment(info.end),
                });
            },
            selectAllow: function(info) {
                return info.start > moment.utc();  // past days are not selectable
            },
            unselectAuto: false, // the selection stays when clicking outside
            selectOverlap: function (event) {
                return false;
            },
            events: function(info, successCallback, failureCallback) {
                var startDate = moment(info.start).add(info.start.getTimezoneOffset(), 'minutes');
                var endDate = moment(info.end).add(info.end.getTimezoneOffset(), 'minutes');
                var start = startDate.format(DATETIME_SERVER_FORMAT);
                var end = endDate.format(DATETIME_SERVER_FORMAT);

                self._fetchUnavailabilities(start, end).then(function (data) {
                    var unavailabilities = self._toCalendarEvent(data['unavailabilities']);
                    var rental = self._toCalendarEvent(data['bookings']);
                    var intervals = rental.concat(unavailabilities);
                    successCallback(intervals);
                });
            },
        };
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    /**
     * Get unavailabilites and rental bookings for all resources of the product, for the current period.
     **/
    _fetchUnavailabilities (startUtc, stopUtc) {
        return this._rpc({
            route: '/shop/rental/'+this.productTemplateId+'/calendar/',
            params: {
                'start': startUtc,
                'stop': stopUtc,
            },
        });
    },
    _toCalendarEvent (data) {
        var self = this;
        var result = [];
        data.forEach(function(item){
            // create the  fullcalendar event
            var values = {
                'start': moment.utc(item[0]).format(),
                'end': moment.utc(item[1]).format(),
                'allDay': true, // default
            };
            if (self.rentalMinDuration && _.contains(['day', 'week', 'month'], self.rentalMinDuration)) {
                values['end'] = moment.utc(item[1]).endOf('day').format(); //
            }


            if (_.contains(['draft', 'confirmed'], item[2])) {
                values['classNames'] = item[2] == 'draft' ? ['bg-warning'] : ['bg-danger'];
            } else { // unavailability
                values['backgroundColor'] = 'grey';
                values['rendering'] = 'background';
                if (self.rentalMinDuration && _.contains(['hour', 'minute'], self.rentalMinDuration)) {
                    values['allDay'] = false;
                }
            }
            result.push(values);
        });
        return result;
    },
    _unavailabilitiesToCalendarEvent (data) {
        var self = this;
        var result = [];
        data.forEach(function(item){
            // create the  fullcalendar event
            var values = {
                'start': moment.utc(item[0]).format(),
                'end': moment.utc(item[1]).format(),
                'rendering': 'background',
                'backgroundColor': 'grey',
                'allDay': false, // default
            };
            if (self.rentalMinDuration && _.contains(['day', 'week', 'month'], self.rentalMinDuration)) {
                values['allDay'] = true;
            }
            result.push(values);
        });
        return result;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

});
});
