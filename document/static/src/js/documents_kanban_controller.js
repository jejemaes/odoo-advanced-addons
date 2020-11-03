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

});

return DocumentsKanbanController;

});