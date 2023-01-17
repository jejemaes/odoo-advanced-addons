odoo.define('document.DocumentKanbanRecord', function (require) {
'use strict';

const KanbanRecord = require('web.KanbanRecord');
const fileUploadMixin = require('web.fileUploadMixin');

const DocumentKanbanRecord = KanbanRecord.extend(fileUploadMixin, {
    events: Object.assign({}, KanbanRecord.prototype.events, fileUploadMixin.events, {
        'click .oe_kanban_previewer': '_onImageClicked',
        'click .oe_kanban_upload': '_onUploadClicked',
    }),

    /**
     * @override
    */
    init() {
        this._super(...arguments);
        fileUploadMixin.init.apply(this, arguments);
    },
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
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onUploadClicked(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.trigger_up('set_request_file', {
            id: this.id,
        })
    },
});

return DocumentKanbanRecord;

});