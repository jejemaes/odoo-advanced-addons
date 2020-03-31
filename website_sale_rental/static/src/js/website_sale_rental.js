odoo.define('website_sale_rental.rental_button', function (require) {
    'use strict';

    require('web_editor.ready');

    var RentalModal = require('website_sale_rental.button_and_modal').RentalModal;
    var RentalButton = require('website_sale_rental.button_and_modal').RentalButton;
    var root = require('root.widget');

    var $elems = $('.o_rental_order_btn');
    if (!$elems.length) {
        return null;
    }

    var buttons = [];
    $elems.each(function() {
        var $elem = $(this);
        var button = new RentalButton(root);
        button.attachTo($elem);
        buttons.push(button);
    });

});
