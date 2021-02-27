
odoo.define('pos_customer_required.PaymentScreen', function (require) {
    'use strict';

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');

    const CustomerRequiredPaymentScreen = (PaymentScreen) =>
        class extends PaymentScreen {
            async validateOrder(isForceValidate) {
                if(this.env.pos.config.require_customer == 'payment' && !this.currentOrder.get_client()){
                    this.showPopup('ConfirmPopup', {
                        'title': this.env._t('An anonymous order cannot be confirmed'),
                        'body':  this.env._t('Please select a customer for this order.'),
                    });
                    return this.selectClient();
                }
                return super.validateOrder();
            }
        };

    Registries.Component.extend(PaymentScreen, CustomerRequiredPaymentScreen);

    return CustomerRequiredPaymentScreen;
});



odoo.define('pos_customer_required.ProductScreen', function (require) {
    'use strict';

    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');

    const CustomerRequiredProductScreen = (ProductScreen) =>
        class extends ProductScreen {
            _onClickPay () {
                if(this.env.pos.config.require_customer == 'order' && !this.currentOrder.get_client()){
                    this.showPopup('ConfirmPopup', {
                        'title': this.env._t('An anonymous order cannot be confirmed'),
                        'body':  this.env._t('Please select a customer for this order.'),
                    });
                    return this._onClickCustomer();
                }
                return super._onClickPay();
            }
        };

    Registries.Component.extend(ProductScreen, CustomerRequiredProductScreen);

    return CustomerRequiredProductScreen;
});
