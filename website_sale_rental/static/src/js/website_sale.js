odoo.define('website_sale_rental.website_sale', function (require) {
    'use strict';

    var sAnimations = require('website.content.snippets.animation');

    /**
     * Adds the handler to allow removing the rental sale line, without passing by the
     * editable quantity input.
     */
    sAnimations.registry.WebsiteSale.include({
        events: _.extend({}, sAnimations.registry.WebsiteSale.prototype.events, {
            'click .js_delete_rental_product': '_onClickDeleteRentalProduct',
        }),
        _onClickDeleteRentalProduct: function (ev){
            var $btn = $(ev.currentTarget);
            var $dom = $btn.closest('tr');
            var $input = $dom.find('.js_quantity').first();

            var $dom_optional = $dom.nextUntil(':not(.optional_product.info)');
            var line_id = parseInt($input.data('line-id'), 10);
            var productIDs = [parseInt($input.data('product-id'), 10)];
            this._changeCartQuantity($input, 0, $dom_optional, line_id, productIDs);
        },
    });

});
