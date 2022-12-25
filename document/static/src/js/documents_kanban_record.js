odoo.define('document.DocumentKanbanRecord', function (require) {
'use strict';

const KanbanRecord = require('web.KanbanRecord');

const DocumentKanbanRecord = KanbanRecord.extend({
    events: Object.assign({}, KanbanRecord.prototype.events, {
        'click .oe_kanban_previewer': '_onImageClicked',
    }),

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onImageClicked(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.trigger_up('kanban_image_clicked', {
            recordList: [this.recordData],
            recordId: this.recordData.id
        });
    },
});

return DocumentKanbanRecord;

});