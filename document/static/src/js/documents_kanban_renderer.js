odoo.define('documents.DocumentsKanbanRenderer', function (require) {
'use strict';

const DocumentsKanbanRecord = require('documents.DocumentsKanbanRecord');
const KanbanRenderer = require('web.KanbanRenderer');

const DocumentsKanbanRenderer = KanbanRenderer.extend({
    config: Object.assign({}, KanbanRenderer.prototype.config, {
        KanbanRecord: DocumentsKanbanRecord,
    }),

    /**
     * @override
     */
    async start() {
        this.$el.addClass('o_documents_kanban_view o_documents_view position-relative align-content-start flex-grow-1 flex-shrink-1');
        await this._super(...arguments);
    },
});

return DocumentsKanbanRenderer;

});