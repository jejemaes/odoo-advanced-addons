/** @odoo-module **/

import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { FileUploadProgressBar } from "@web/core/file_upload/file_upload_progress_bar";
import { KANBAN_BOX_ATTRIBUTE } from "@web/views/kanban/kanban_arch_parser";
import { useBus, useService } from "@web/core/utils/hooks";
import { useFileViewer } from "@document/file_viewer/file_viewer_hook";
import { FileModelMixin } from "@document/file_viewer/file_model";
import { useRef } from "@odoo/owl";

const CANCEL_GLOBAL_CLICK = ["a", ".dropdown", ".oe_kanban_action"].join(",");


export class DocumentFileModel extends FileModelMixin(Object) {}


export class DocumentKanbanRecord extends KanbanRecord {
    setup() {
        super.setup();
        this.fileViewer = useFileViewer();

        this.uploadFileInput = useRef("uploadFileInput");
        this.uploadService = useService("file_upload");
        useBus(
            this.uploadService.bus,
            "FILE_UPLOAD_LOADED",
            () => {
                this.props.record.model.load();
            },
        );
    }

    async onInputChange(ev) {
        if (!ev.target.files) {
            return;
        }
        this.uploadService.upload(
            "/document/upload_file",
            ev.target.files,
            {
                buildFormData: (formData) => {
                    formData.append("document_id", this.props.record.data.id);
                },
            },
        );
        ev.target.value = "";
    }

    /**
     * @override
     */
    onGlobalClick(ev) {
        if (ev.target.closest(CANCEL_GLOBAL_CLICK)) {
            return;
        }
        // Preview is clicked
        if (ev.target.closest("div.oe_kanban_previewer")) {
            const attachmentId = this.props.record.data.attachment_id;
            const attachment = Object.assign(new DocumentFileModel(), {
                id: attachmentId ? attachmentId[0] : null,
                filename: this.props.record.data.name,
                name: this.props.record.data.name,
                mimetype: this.props.record.data.mimetype,
                checksum: this.props.record.data.checksum,
                type: this.props.record.data.document_type,
                access_token: this.props.record.data.access_token,
                url: this.props.record.data.url,
            });
            this.fileViewer.open(attachment)
            return;
        }
        // On upload is clicked
        if (ev.target.closest("div.o_document_upload_request")) {
            this.uploadFileInput.el.click();
            return;
        }
        return super.onGlobalClick(ev);
    }
}
