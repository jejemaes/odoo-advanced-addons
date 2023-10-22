odoo.define('@document/views/kanban/document_kanban_controller', async function (require) {
'use strict';
let __exports = {};
/** @odoo-module **/

const { patch } = require('@web/core/utils/patch');
const { KanbanController } = require("@web/views/kanban/kanban_controller");

const { DocumentUpload } =  require('@document/mixins/document_upload');


const DocumentKanbanController = __exports.DocumentKanbanController = class DocumentKanbanController extends KanbanController {
    setup() {
        super.setup(...arguments);
    }

    async onCreateRecord(ev){
        const defaultType = $(ev.currentTarget).data('default-type');
        if (defaultType == 'request') {
            this.actionService.doAction('document.action_document_request', {
                onClose: () => this.model.load(),
                additionalContext: { default_document_type: defaultType }
            });
        } else {
            this.actionService.doAction({
                type: 'ir.actions.act_window',
                views: [[false, 'form']],
                res_model: this.props.resModel,
                context: {
                    default_document_type: defaultType,
                }
            });
        }
    }
}
patch(DocumentKanbanController.prototype, 'document_kanban_controller_upload', DocumentUpload);


return __exports;
});
;