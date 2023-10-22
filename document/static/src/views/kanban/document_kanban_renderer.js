/** @odoo-module **/

import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { useService } from "@web/core/utils/hooks";
import { DocumentKanbanRecord } from "@document/views/kanban/document_kanban_record";

export class DocumentKanbanRenderer extends KanbanRenderer {}

DocumentKanbanRenderer.components = Object.assign({}, KanbanRenderer.components, {
    KanbanRecord: DocumentKanbanRecord,
})
