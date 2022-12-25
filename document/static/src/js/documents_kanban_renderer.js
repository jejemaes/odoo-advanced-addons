odoo.define('document.DocumentKanbanRenderer', function (require) {
'use strict';

const DocumentKanbanRecord = require('document.DocumentKanbanRecord');
const KanbanRenderer = require('web.KanbanRenderer');

const DocumentKanbanRenderer = KanbanRenderer.extend({
    config: Object.assign({}, KanbanRenderer.prototype.config, {
        KanbanRecord: DocumentKanbanRecord,
    }),

    /**
     * @override
     */
    async start() {
        this.$el.addClass('o_documents_kanban_view o_documents_view position-relative align-content-start flex-grow-1 flex-shrink-1');
        await this._super(...arguments);
    },
});

return DocumentKanbanRenderer;

});