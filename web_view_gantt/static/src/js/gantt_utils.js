odoo.define('web_view_gantt.GanttUtils', function (require) {
"use strict";

var core = require('web.core');
var config = require('web.config');
var time = require('web.time');
var session = require('web.session');
var fieldUtils = require('web.field_utils');

var _t = core._t;


/**
 * Convert date to server timezone
 *
 * @param {Moment} date
 * @returns {string} date in server format
 */
var convertToServerDatetime = function (date) {
    var result = date.clone();
    if (!result.isUTC()) {
        result.subtract(session.getTZOffset(date), 'minutes');
    }
    return result.locale('en').format('YYYY-MM-DD HH:mm:ss');
};
/**
 * Format field value to display purpose.
 *
 * @private
 * @param {any} value
 * @param {Object} field
 * @returns {string} formatted field value
 */
var formatFieldValue = function (value, field) {
    var options = {};
    if (field.type === 'boolean') {
        options = {forceString: true};
    }
    var formattedValue = fieldUtils.format[field.type](value, field, options);
    return formattedValue || _.str.sprintf(_t('Undefined %s'), field.string);
};

return {
	convertToServerDatetime: convertToServerDatetime,
	formatFieldValue: formatFieldValue,
};

});

