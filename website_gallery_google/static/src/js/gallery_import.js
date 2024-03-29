odoo.define('website_gallery.import_buttons', function (require) {
"use strict";

var config = require('web.config');
var KanbanController = require('web.KanbanController');
var KanbanView = require('web.KanbanView');
var ListController = require('web.ListController');
var ListView = require('web.ListView');


// Mixins that enable the 'Import' feature
var ImportViewMixin = {
    /**
     * @override
     * @param {Object} params
     * @param {boolean} [params.import_enabled=true] determine if the import
     *   button is visible (in the control panel)
     */
    init: function (viewInfo, params) {
        var importEnabled = 'import_enabled' in params ? params.import_enabled : true;
        this.controllerParams.importEnabled = importEnabled && !config.device.isMobile;
    },
};

var ImportControllerMixin = {
    /**
     * @override
     */
    init: function (parent, model, renderer, params) {
        this.importEnabled = params.importEnabled;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Adds an event listener on the import button.
     *
     * @private
     */
    _bindImport: function () {
        if (!this.$buttons) {
            return;
        }
        var self = this;
        this.$buttons.on('click', '.o_button_gallery_import', function () {
            var state = self.model.get(self.handle, {raw: true});
            self.do_action('website_gallery_google.website_gallery_import_google_action', {
                'additional_context': {'active_model': state.model}
            });
        });
    }
};

// Activate 'Import' feature on List views
ListView.include({
    init: function () {
        this._super.apply(this, arguments);
        ImportViewMixin.init.apply(this, arguments);
    },
});

ListController.include({
    init: function () {
        this._super.apply(this, arguments);
        ImportControllerMixin.init.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Extends the renderButtons function of ListView by adding an event listener
     * on the import button.
     *
     * @override
     */
    renderButtons: function () {
        this._super.apply(this, arguments); // Sets this.$buttons
        if (this.modelName === 'website.gallery') {
            ImportControllerMixin._bindImport.call(this);
        }
    }
});

// Activate 'Import' feature on Kanban views
KanbanView.include({
    init: function () {
        this._super.apply(this, arguments);
        ImportViewMixin.init.apply(this, arguments);
    },
});

KanbanController.include({
    init: function () {
        this._super.apply(this, arguments);
        ImportControllerMixin.init.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Extends the renderButtons function of ListView by adding an event listener
     * on the import button.
     *
     * @override
     */
    renderButtons: function () {
        this._super.apply(this, arguments); // Sets this.$buttons
        if (this.modelName === 'website.gallery') {
            ImportControllerMixin._bindImport.call(this);
        }
    }
});

});
