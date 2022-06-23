odoo.define('documents.DocumentsKanbanView', function (require) {
'use strict';

const DocumentsKanbanController = require('documents.DocumentsKanbanController');
const DocumentsKanbanRenderer = require('documents.DocumentsKanbanRenderer');

const KanbanView = require('web.KanbanView');
const viewRegistry = require('web.view_registry');

const { _lt } = require('web.core');

const DocumentsKanbanView = KanbanView.extend({
    config: Object.assign({}, KanbanView.prototype.config, {
        Controller: DocumentsKanbanController,
        Renderer: DocumentsKanbanRenderer,
    }),
    display_name: _lt('Documents Kanban'),
});

viewRegistry.add('document_kanban', DocumentsKanbanView);

return DocumentsKanbanView;

});