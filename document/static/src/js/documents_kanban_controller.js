odoo.define('documents.DocumentsKanbanController', function (require) {
'use strict';

const MailDocumentViewer = require('mail.DocumentViewer');
const KanbanController = require('web.KanbanController');

var DocumentViewer = MailDocumentViewer.extend({

    init(parent, attachments, activeAttachmentID) {
        this._super(...arguments);
        this.modelName = 'document.document';
    },
});

var DocumentsKanbanController = KanbanController.extend({
    buttons_template: 'DocumentKanbanView.buttons',
    events: Object.assign({}, KanbanController.prototype.events, {
        'click a.o-kanban-button-new-document': '_onCreateNewDocument',
    }),
    custom_events: Object.assign({}, KanbanController.prototype.custom_events, {
        kanban_image_clicked: '_onKanbanImageClicked'
    }),

    /**
     * @private
     * @param {OdooEvent} ev
     * @param {integer} ev.data.recordId
     * @param {boolean} ev.data.openPdfManager
     * @param {Array<Object>} ev.data.recordList
     */
    async _onKanbanImageClicked(ev) {
        ev.stopPropagation();
        const documents = ev.data.recordList;
        const recordId = ev.data.recordId;
        const documentViewer = new DocumentViewer(this, documents, recordId);
        await documentViewer.appendTo(this.$('.o_documents_view'));
    },

    renderButtons: function ($node) {
        this._super(...arguments);

        // hide dropdown if empty
        if (this.$buttons) { // if user has not the 'create' access right, buttons are undefined
            if (this.$buttons.find('.o_document_kanban_btn_list_dropdown > a').length === 1) {
                this.$buttons.find('#o_document_kanban_btn_list').hide();
            } else {
                this.$buttons.on('click', '.o_document_kanban_btn_list_dropdown > a.o-kanban-button-new', this._onButtonNew.bind(this));
            }
        }
    },
    /**
     * Handler to open form view with correct default document handler in context
     *
     **/
    _onCreateNewDocument: function(ev) {
        const handler = $(ev.currentTarget).data('handler');
        this.do_action({
            type: 'ir.actions.act_window',
            views: [[false, 'form']],
            res_model: this.modelName,
            context: {
                default_handler: handler,
            }
        });
    },

});

return DocumentsKanbanController;

});