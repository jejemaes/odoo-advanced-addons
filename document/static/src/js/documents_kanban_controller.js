odoo.define('document.DocumentKanbanController', function (require) {
'use strict';

const MailDocumentViewer = require('@mail/js/document_viewer')[Symbol.for("default")];

const KanbanController = require('web.KanbanController');

const fileUploadMixin = require('web.fileUploadMixin');
const { _t, qweb } = require('web.core');

console.log('=========', MailDocumentViewer);

var DocumentViewer = MailDocumentViewer.extend({

    init(parent, attachments, activeAttachmentID) {
        this._super(...arguments);
        this.modelName = 'document.document';
    },
});


var DocumentKanbanController = KanbanController.extend(fileUploadMixin, {
    buttons_template: 'DocumentKanbanView.buttons',
    events: Object.assign({}, KanbanController.prototype.events, fileUploadMixin.events, {
        'click .o-kanban-button-new-document': '_onCreateNewDocument',
        'click .o-kanban-button-upload-document': '_onClickUploadDocument',
    }),
    custom_events: Object.assign({}, KanbanController.prototype.custom_events, fileUploadMixin.custom_events, {
        kanban_image_clicked: '_onKanbanImageClicked'
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
            if (this.$buttons.find('.o_document_kanban_btn_list_dropdown > a').length === 0) {
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


    /**
     * Upload Document Mixin
     **/

    _onClickUploadDocument: function(ev) {
        this._uploadFilesHandler(true)(ev);
    },
    /**
     * Generates a handler for uploading one or multiple file(s)
     *
     * @private
     * @param {boolean} multiple allow to upload a single file or multiple files
     * @returns {Function}
     */
    _uploadFilesHandler(multiple) {
        return (ev) => {
            const recordId = ev.data ? ev.data.id : undefined;
            const $uploadInput = this.hiddenUploadInputFile
                ? this.hiddenUploadInputFile.off('change')
                : (this.hiddenUploadInputFile = $('<input>', { type: 'file', name: 'files[]', class: 'o_hidden' }).appendTo(this.$el));
            $uploadInput.attr('multiple', multiple ? true : null);
            const cleanup = $.prototype.remove.bind($uploadInput);
            $uploadInput.on('change', async changeEv => {
                await this._uploadFiles(changeEv.target.files, { recordId }).finally(cleanup);
            });
            this._promptFileInput($uploadInput);
        };
    },
    /**
     * Used in the tests to mock the upload behaviour and to access the $uploadInput fragment.
     *
     * @private
     * @param {jQueryElement} $uploadInput
     */
    _promptFileInput($uploadInput) {
        $uploadInput.click();
    },

     /**
     * @override
     */
    _getFileUploadRoute() {
        return '/document/upload_file';
    },
    /**
     * @override
     * @param {Object} param0
     * @param {XMLHttpRequest} param0.xhr
     */
    _onUploadLoad({ xhr }) {
        const result = xhr.status === 200
            ? JSON.parse(xhr.response)
            : {
                error: _.str.sprintf(_t("status code: %s, message: %s"), xhr.status, xhr.response)
            };
        if (result.error) {
            this.displayNotification({ title: _t("Error"), message: result.error, sticky: true });
        } else if (result.ids && result.ids.length > 0) {
            this._selectedRecordIds = result.ids;
        }
        fileUploadMixin._onUploadLoad.apply(this, arguments);
    },
    /**
     * @override
     * @param {integer} param0.recordId
     */
    _makeFileUploadFormDataKeys({ recordId }) {
        const context = this.model.get(this.handle, { raw: true }).getContext();

        // Helpers
        const isFolderCategory = (s) => s.type === "category" && s.fieldName === "folder_id";
        const isTagFilter = (s) => s.type === "filter" && s.fieldName === "tag_ids";

        const tagsSection = this.searchModel.get('sections').filter(isTagFilter)[0];
        const folderSection = this.searchModel.get('sections').filter(isFolderCategory)[0];

        const selectedTagIds = [...tagsSection.values.values()].filter((value) => value.checked).map((value) => value.id);
        let selectedFolderId;
        if (folderSection) {
            selectedFolderId = folderSection.activeValueId;
        } else {
            selectedFolderId = 'default_folder_id' in context ? context['default_folder_id'] : '';
        }

        return {
            folder_id: selectedFolderId || '',
            tag_ids: selectedTagIds,
        };
    },

});

return DocumentKanbanController;

});