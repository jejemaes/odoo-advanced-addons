/** @odoo-module */

import { registry } from '@web/core/registry';
import { kanbanView } from '@web/views/kanban/kanban_view';
import { DocumentKanbanController } from '@document/views/kanban/document_kanban_controller';
import { DocumentKanbanRenderer } from '@document/views/kanban/document_kanban_renderer';

registry.category('views').add('document_kanban', {
    ...kanbanView,
    buttonTemplate: 'document.KanbanButtons',
    Controller: DocumentKanbanController,
    Renderer: DocumentKanbanRenderer,
});
