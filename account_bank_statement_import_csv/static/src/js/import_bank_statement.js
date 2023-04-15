odoo.define('bank_stmt_import_csv.import', function (require) {
"use strict";

var core = require('web.core');
var BaseImport = require('base_import.import')

var _t = core._t;


/**
 * Parameters for this action are
 * - import_wizard_id: integer, reprenseting the db id of the already created `base_import.import` instance.
 * - filename: string, the filename of imported file
 *
 **/
var ImportBankStatement = BaseImport.DataImport.extend({
    init: function (parent, action) {
        //action.display_name = _t('Import Bank Statement'); // Displayed in the breadcrumbs
        this._super.apply(this, arguments);
        // specific params for this extended action
        this.filename = action.params.filename || 'no file';
        this.import_wizard_id = action.params.import_wizard_id;
        this.first_load = true;
        this.statement_id = null;  // populate in return of 'execute_import'
    },
    start: function () {
        var self = this;
        return this._super().then(function (res) {
            // do like super() does, and that was prevent by the `create_model` returning empty promise.
            self.id = self.import_wizard_id;
            self.$('input[name=import_id]').val(self.import_wizard_id);
            // next step in the state machine
            self['loaded_file']();
        });
    },
    create_model: function() {
        return Promise.resolve();
    },
    import_options: function () {
        var options = this._super();
        options['importing_bank_statement'] = true;
        return options;
    },
    onfile_loaded: function () {
        var self = this;
        if (this.first_load) {
            this.$('.oe_import_file_show').val(this.filename);
            this.$('.oe_import_file_reload').hide();
            this.first_load = false;
            self['settings_changed']();
        } else {
            this.$('.oe_import_file_reload').show();
            this._super();
        }
    },
    call_import: function(kwargs) {
        var self = this;
        var promise = this._super.apply(this, arguments);
        promise.then(function (response) {
            if (response.messages) {
                var typeList = _.pluck(response.messages, 'type');
                var hasBankStmtType = _.any(typeList, function (item) {
                    return item == 'bank_statement';
                });
                if (hasBankStmtType) {
                    _.each(response.messages, function(item) {
                        if (item.type && item.type == 'bank_statement') {
                            self.statement_id = item.statement_id
                        }
                    });
                }
            }
        });
        return promise;
    },
    exit: function () {
        if (!this.statement_id) return;
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: 'account.bank.statement',
            res_id: this.statement_id,
            views: [[false, 'form']],
            target: 'current',
        });
    },
});
core.action_registry.add('bank_statement_import', ImportBankStatement);

return {
    ImportBankStatement: ImportBankStatement,
};
});
