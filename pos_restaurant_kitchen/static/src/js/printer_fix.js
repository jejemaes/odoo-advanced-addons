odoo.define('pos_restaurant_kitchen.PrinterFix', function (require) {
"use strict";

var PrinterMixin = require('point_of_sale.Printer').PrinterMixin;

/**
 Monkey Patch for printer return values
**/
PrinterMixin['print_receipt'] = async function(receipt) {
    if (receipt) {
        this.receipt_queue.push(receipt);
    }
    let image, sendPrintResult;
    while (this.receipt_queue.length > 0) {
        receipt = this.receipt_queue.shift();
        image = await this.htmlToImg(receipt);
        try {
            sendPrintResult = await this.send_printing_job(image);
        } catch (error) {
            this.receipt_queue.length = 0;
            return this.printResultGenerator.IoTActionError();
        }
        // This is the fixed line
        if (!sendPrintResult || (_.contains(sendPrintResult, 'result') && !sendPrintResult.result)) {
            this.receipt_queue.length = 0;
            return this.printResultGenerator.IoTResultError();
        }
    }
    return this.printResultGenerator.Successful();
};

});
