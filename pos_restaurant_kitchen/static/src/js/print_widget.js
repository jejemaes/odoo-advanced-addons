odoo.define('pos_restaurant_kitchen.PrintWidget', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');

const session = require('web.session');
var field_registry = require('web.field_registry');




var PrintWidget = AbstractField.extend({
    events: _.extend({}, AbstractField.prototype.events, {
        'click': '_onClick'
    }),
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Display button
     * @override
     * @private
     */
    _render: function () {
        if (this.value) {
            this.$el.html('<button class="btn btn-primary"><i class="fa fa-print"/> Print</button>');
            this.$el.attr('title', this.value);
            this.$el.attr('aria-label', this.value);
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Open link button
     *
     * @private
     * @param {MouseEvent} event
     */
    _onClick: function (event) {
        event.stopPropagation();
        var PrintWindow = window.open(this.value, '_new');

        return;
        var Pagelink = "about:blank";
        var pwa = window.open(Pagelink, "_new");
        pwa.document.open();
        pwa.document.write(this._getHtmlPrintPage(this.value));
        pwa.document.close();
    },
    _getHtmlPrintPage: function(source) {
        return "<html><head><script>function step1(){\n" +
                "setTimeout('step2()', 10);}\n" +
                "function step2(){window.print();window.close()}\n" +
                "</script></head><body onload='step1()'>\n" +
                "<img src='" + source + "' /></body></html>";
    }
});


field_registry.add('restaurant_print', PrintWidget);

return PrintWidget;

});
