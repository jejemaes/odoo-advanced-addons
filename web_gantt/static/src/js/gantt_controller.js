/** @odoo-module */

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";
import { useModel } from "@web/views/model";
import { standardViewProps } from "@web/views/standard_view_props";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

import { Component, onWillStart, onWillUpdateProps, onWillUnmount, onWillDestroy } from "@odoo/owl";
import { SCALES } from "./gantt_arch_parser";


export class GanttController extends Component {

    static components = {
        Layout,
        Dropdown,
        DropdownItem,
    };
    static props = {
        ...standardViewProps,
        Model: Function,
        Renderer: Function,
        buttonTemplate: String,
        archInfo: Object,
        formViewId: [Boolean, Number],
    };
    static template = "web_gantt.GanttController";

	setup() {
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.orm = useService("orm");

        this.model = useModel(this.props.Model, {
            resModel: this.props.resModel,
            domain: this.props.domain,
            fields: this.props.fields,
            archInfo: this.props.archInfo,
        });
    }

    get canCreate() {
        return this.model.metaData.archInfo.activeActions.create;
    }

    get canEdit() {
        return this.model.metaData.archInfo.activeActions.edit;
    }

    get canDelete() {
        return this.model.metaData.archInfo.activeActions.delete;
    }

    get allowedScales() {
        return this.model.allowedScales;
    }

    get scaleId() {
        return this.model.metaData.scale.id;
    }

    get scaleLabels() {
        const labelsMap = {};
        Object.keys(this.model.allowedScales).forEach((scaleId) => {
            labelsMap[scaleId] = SCALES[scaleId].description;
        });
        return labelsMap;
    }

    async setDate(move) {
        let focusDate = null;
        switch (move) {
            case "next":
                focusDate = this.model.metaData.focusDate.plus({ [`${this.model.metaData.scale.id}s`]: 1 });
                break;
            case "previous":
                focusDate = this.model.metaData.focusDate.minus({ [`${this.model.metaData.scale.id}s`]: 1 });
                break;
            case "today":
                focusDate = luxon.DateTime.local().startOf("day");
                break;
        }
        await this.model.load({ focusDate });
    }

    async setScale(scaleId){
        this.model.load({ scaleId });
    }

    /**
     * Opens dialog to add/edit/view a record
     *
     * @param {Record<string, any>} props FormViewDialog props
     * @param {Record<string, any>} [options={}]
     */
    openDialog(props, options = {}) {
        const { resModel, formViewId: viewId } = this.model.metaData;
        const title = props.title || (props.resId ? _t("Open") : _t("Create"));

        let removeRecord;
        if (this.canDelete && props.resId) {
            removeRecord = () => {
                return new Promise((resolve) => {
                    this.dialogService.add(ConfirmationDialog, {
                        body: _t("Are you sure to delete this record?"),
                        confirm: async () => {
                            await this.orm.unlink(resModel, [props.resId]);
                            resolve();
                        },
                        cancel: () => {},
                    });
                });
            };
        }

        this.closeDialog = this.dialogService.add(
            FormViewDialog,
            {
                title,
                resModel,
                viewId,
                resId: props.resId,
                mode: this.canEdit ? "edit" : "readonly",
                context: props.context,
                removeRecord,
            },
            {
                ...options,
                onClose: () => {
                    this.closeDialog = null;
                    this.model.load();
                },
            }
        );
    }
}
