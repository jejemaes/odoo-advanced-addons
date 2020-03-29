odoo.define('rental.CalendarView', function (require) {
"use strict";

var CalendarView = require('web.CalendarView');
var CalendarModel = require('web.CalendarModel');
var viewRegistry = require('web.view_registry');

/**
 * Extend this to remove 1 second at the end date, when creating an event. The
 * goal is to have the end of the interval inclusif to stay consistent with the
 * backend.
 */
var RentalCalendarModel = CalendarModel.extend({
    calendarEventToRecord: function (event) {
        var result = this._super.apply(this, arguments);
        if (result[this.mapping.date_stop] && !event.id) {
            result[this.mapping.date_stop] = result[this.mapping.date_stop].subtract(1, 'seconds');
        }
        return result;
    },
});


var RentalCalendarView = CalendarView.extend({
    config: _.extend({}, CalendarView.prototype.config, {
        Model: RentalCalendarModel,
    }),
});

viewRegistry.add('rental_calendar_view', RentalCalendarView);

return RentalCalendarView;

});