odoo.define('pos_restaurant_kitchen.AutoRefreshKanbanView', function (require) {
"use strict";

var KanbanView = require('web.KanbanView');
var KanbanController = require('web.KanbanController');
var KanbanModel = require('web.KanbanModel');
var view_registry = require('web.view_registry');
const session = require('web.session');


var AutoRefreshKanbanModel = KanbanModel.extend({
    _audio: false,

    _readGroup: function (list, options) {
        var self = this;
        var result = this._super(list, options);
        result.then(function(data){
            if (data.count) {
                self._beep();
            }
        });
        return result;
    },
    _beep: function () {
        if (typeof(Audio) !== "undefined") {
            if (!this._audio) {
                this._audio = new Audio();
                //var ext = this._audio.canPlayType("audio/ogg; codecs=vorbis") ? ".ogg" : ".mp3";
                this._audio.src = "/pos_restaurant_kitchen/static/audio/ding-ding-sound.mp3";
            }
            Promise.resolve(this._audio.play()).catch(_.noop);
        }
    },

});

var AutoRefreshKanbanController = KanbanController.extend({

    /**
     * @override
     */
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);

        var actionContext = this.initialState.getContext();
        if ('kanban_autorefresh' in actionContext) {
            var self = this;
            this._refresh_timeout = setInterval(function() {
                self.reload();
            }, actionContext['kanban_autorefresh']);
        } else {
            this._refresh_timeout = false;
        }
    },
    /**
     * @override
     */
    destroy: function () {
        if (this._refresh_timeout) {
            clearInterval(this._refresh_timeout);
        }
        return this._super();
    },
});

var AutoRefreshKanbanView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Controller: AutoRefreshKanbanController,
        Model: AutoRefreshKanbanModel,
    }),
});


view_registry.add('autorefresh_kanban', AutoRefreshKanbanView);

return AutoRefreshKanbanView;

});
