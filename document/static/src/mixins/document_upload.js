/** @odoo-module */

import { useBus, useService } from '@web/core/utils/hooks';
import { sprintf } from "@web/core/utils/strings";

const { useRef, useEffect, useState, useEnv } = owl;

// Helpers (applied on searchModel)
const isFolderCategory = (s) => s.type === "category" && s.fieldName === "folder_id";
const isTagFilter = (s) => s.type === "filter" && s.fieldName === "tag_ids";


export const DocumentUpload = {
    setup() {
        this._super();
        this.notification = useService('notification');
        this.http = useService('http');
        this.fileInput = useRef('fileInput');
        this.root = useRef("root");

        useBus(this.env.bus, "change_file_input", async (ev) => {
            this.fileInput.el.files = ev.detail.files;
            await this.onChangeFileInput();
        });
    },

    uploadDocument() {
        this.fileInput.el.click();
    },

    async onChangeFileInput() {
        // Need to call `http.post` as text, so each dict key must be an string (tag_ids is comma separated ID list).
        const folderId = this.getSelectedFolderId();
        const tagIds = this.getSelectedTagIds();
        const params = {
            csrf_token: odoo.csrf_token,
            ufile: [...this.fileInput.el.files],
            folder_id: folderId || null,
            tag_ids: tagIds.join(','),
        };
        const response = await this.http.post('/document/upload_file', params, "text");
        this.onUpload(JSON.parse(response));
    },

    async onUpload(data) {
        if (data.error) {
            this.notification.add(
                sprintf(this.env._t('An error occurred during the upload : %s'), data.error),
                {type: 'danger'}
            );
        } else {
            this.notification.add(
                data.success,
                {type: 'success'}
            );
        }
        await this.model.load();
    },
     /**
     * Returns the id of the current selected folder, if any, false
     * otherwise.
     * @returns {number | false}
     */
    getSelectedFolderId() {
        const { activeValueId } = this.env.searchModel.getSections(isFolderCategory)[0];
        return activeValueId;
    },
    /**
     * Returns ids of selected tags.
     * @returns {number[]}
     */
    getSelectedTagIds() {
        const { values } = this.env.searchModel.getSections(isTagFilter)[0];
        return [...values.values()].filter((value) => value.checked).map((value) => value.id);
    }
};