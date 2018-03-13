odoo.define('buzzer.buzzer_page', function (require) {
"use strict";

require('web.dom_ready');
var bus = require('bus.bus').bus;

var buzzer = require('buzzer.buzzer');

var $buzzer_container = $('#o_buzzer_container');
if (!$buzzer_container.length) {
    return $.Deferred().reject("DOM doesn't contain '#o_buzzer_container'");
}


var data = $buzzer_container.data();
var options = {
	'mode_reaonly': false,
	'user_id': data['userId'],
	'channel_uuid': data['channelUuid'],
}

var buzzer_btn = new buzzer.BuzzerButton(null, options);
buzzer_btn.appendTo($buzzer_container).then(function(res) {
	bus.start_polling();
});

});
