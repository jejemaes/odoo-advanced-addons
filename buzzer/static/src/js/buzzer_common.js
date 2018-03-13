odoo.define('buzzer.buzzer', function (require) {
"use strict";

var bus = require('bus.bus').bus;
var core = require('web.core');
var session = require('web.session');
var utils = require('web.utils');
var Widget = require('web.Widget');
var ajax = require('web.ajax');

var _t = core._t;
var QWeb = core.qweb;

var BuzzerButton = Widget.extend({
    template: 'buzzer.button',
    events: {
        "click .o_buzzer_btn": "_onClick"
    },

    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.options = _.defaults(options || {}, {
            user_id: session.uid,
            user_name: session.name,
            channel_uuid: false,
            mode_readonly: false,
        });
        this.set('state', 'ready');
        this.last_notif_buzz = false; // datetime of last receive buzz notif
    },

    willStart: function () {
        return this._super.apply(this, arguments).then(this._load_qweb_template.bind(this));
    },

    start: function () {
        var self = this;
        bus.on('notification', this, function (notifications) {
            _.each(notifications, function (notification) {
                self._on_notification(notification);
            });
        });
        return this._super().then(function(result) {
            self.on("change:state", self, self._updateState);
        });
    },

    _load_qweb_template: function () {
        if (!QWeb.has_template('buzzer.buzzer_button')) {
            var xml_files = ['/buzzer/static/src/xml/buzzer.xml'];
            var defs = _.map(xml_files, function (tmpl) {
                return session.rpc('/web/proxy/load', {path: tmpl}).then(function (xml) {
                    QWeb.add_template(xml);
                });
            });
            return $.when.apply($, defs);
        }
        return $.when();
    },

    _on_notification: function (notification){
        var channel = notification[0];
        var notif = notification[1];
        if((_.isArray(channel) && channel[1] == 'buzzer.channel') || _.isString(channel) && channel == this.options.channel_uuid) {
            if(_.contains(_.keys(notif), '_type') && notif._type == 'buzzer'){
                if(notif.action == 'buzz') {
                    if(!this.last_notif_buzz || notif.buzz_time < this.last_notif_buzz.buzz_time) { // notif should be born earlier than last receive buzz notif to be considered
                        this.last_notif_buzz = notif;
                        if(notif.user_id == this.options.user_id && _.contains(['ready', 'blocked'], this.get('state'))) {
                            this.set('state', 'success');
                        }else{
                            this.set('state', 'blocked');
                        }
                    }
                }
                if(notif.action == 'reset') {
                    this.set('state', 'ready');
                    this.last_notif_buzz = false;
                }
            }
        }
    },

    _updateState: function (){
        var state = this.get('state');
        var $button = this.$el.find('.o_buzzer_btn').first();
        console.log($button);
        $button.removeClass('btn-default');
        $button.removeClass('btn-success');
        $button.removeClass('btn-danger');

        if(state == 'ready') {
            $button.addClass('btn-default');
        }
        if(state == 'success') {
            $button.addClass('btn-success');
        }
        if(state == 'blocked') {
            $button.addClass('btn-danger');
        }
    },

    _onClick: function (ev) {
        var self = this;
        ev.stopPropagation();
        ev.preventDefault();
        if(this.get('state') == 'blocked'){
            return $.when();
        }
        return ajax.rpc('/buzzer/' + this.options.channel_uuid + '/buzz');
    },

});

return {
    BuzzerButton: BuzzerButton
};

});
