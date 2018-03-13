odoo.define('buzzer.client_action', function (require) {
"use strict";

var bus = require('bus.bus').bus;
var core = require('web.core');
var data = require('web.data');
var session = require('web.session');
var Widget = require('web.Widget');

var ControlPanelMixin = require('web.ControlPanelMixin');
var buzzer = require('buzzer.buzzer');

var QWeb = core.qweb;
var _t = core._t;


var BuzzerChannelPanel = Widget.extend(ControlPanelMixin, {
    template: 'buzzer.client_action',
    events: {
        'click .o_buzzer_btn_reset': '_onClickReset',
        'click .o_buzzer_btn_stop': '_onClickStop',
    },

    /**
     * @override
     */
    init: function (parent, action, options) {
    	this._super.apply(this, arguments);
        this.action_manager = parent;
        this.options = _.defaults(options || {}, {
            user_id: session.uid,
            channel_id: action.params.channel_id || action.context.active_id,
        });
    },
    /**
     * @override
     */
    willStart: function () {
        return $.when(this._super(), this._setUpData());
    },
    start: function() {
        var self = this;
        return this._super.apply(this, arguments).then(function(result) {
            self._updateControlPanel();
            // listen to buzzer channel
            bus.add_channel(self.channel.uuid);
            bus.start_polling();

            // append buzzer to panel
            self.$('.o_buzzer_admin_participants').empty();
            var defs = [];
            _.each(self.buzzers, function(buzzer) {
                var $container = $('<div class="col-md-4 col-sm-4 col-xs-6"/>');
                self.$('.o_buzzer_admin_participants').append($container);
                defs.push(buzzer.appendTo($container));
            });
            return $.when(defs);
        });
    },

    _setUpData: function (){
    	var self = this;
    	return this._rpc({
    		route: '/buzzer/client_action',
    		params: {
                channel_id: this.options.channel_id,
            }
    	}).then(function(result){
    		self.channel = result.channel;
    		self.participants = result.participants;

            // generate buzer objects
    		self.buzzers = {};
    		_.each(self.participants, function(participant) {
    			var current = new buzzer.BuzzerButton(self, {
    				'user_id': participant.id,
    				'user_name': participant.login,
    				'channel_uuid': self.channel.uuid,
    				'mode_readonly': true,
    			});
    			self.buzzers[participant.id] = current;
    		});
    		return result;
    	});
    },
    /**
     * @private
     */
    _updateControlPanel: function () {
        this.update_control_panel({
            breadcrumbs: this.action_manager.get_breadcrumbs(),
            cp_content: {},
        });
    },
    _onClickReset: function(ev) {
        return this._rpc({
            model: 'buzzer.channel',
            method: 'buzz_reset',
            args: [[this.channel.id]],
        });
    },
    _onClickStop: function(ev) {
        var self = this;
        return this._rpc({
            model: 'buzzer.channel',
            method: 'action_reset_responsible',
            args: [[this.channel.id], {'redirect': true}],
        }).then(function(){
            self.do_action('history_back');
        });
    }


});

core.action_registry.add('buzzer.channel.panel', BuzzerChannelPanel);

return BuzzerChannelPanel;

});
