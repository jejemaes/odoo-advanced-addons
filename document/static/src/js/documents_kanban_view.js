odoo.define('document.DocumentKanbanView', function (require) {
'use strict';

/**
 * This file defines the DocumentsKanbanView, a JS extension of the KanbanView
 * to deal with documents.
 *
 * Warning: there is no groupby menu in this view as it doesn't support the
 * grouped case. Its elements assume that the data isn't grouped.
 */

const DocumentKanbanController = require('document.DocumentKanbanController');
const DocumentKanbanRenderer = require('document.DocumentKanbanRenderer');

const KanbanView = require('web.KanbanView');
const viewRegistry = require('web.view_registry');

const { _lt } = require('web.core');

const DocumentKanbanView = KanbanView.extend({
    config: Object.assign({}, KanbanView.prototype.config, {
        Controller: DocumentKanbanController,
        Renderer: DocumentKanbanRenderer,
    }),
});

viewRegistry.add('document_kanban', DocumentKanbanView);

return DocumentKanbanView;

});
;
