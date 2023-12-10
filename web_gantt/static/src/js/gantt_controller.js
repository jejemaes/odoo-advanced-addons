/** @odoo-module */

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { Layout } from "@web/search/layout";
import { useModel } from "@web/views/model";
import { standardViewProps } from "@web/views/standard_view_props";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";

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

    get rendererProps() {
        return {
            deleteDependency: this.deleteDependency.bind(this),
            planRecords: this.planRecords.bind(this),
            model: this.model,
            openRecord: this.openRecord.bind(this),
            setDate: this.setDate.bind(this),
        };
    }

    /* Actions */

    deleteDependency(srcRecord, dstRecord) {
        this.dialogService.add(ConfirmationDialog, {
            body: sprintf(this.env._t("Are you sure that you want to dependency from %s to %s ?"), srcRecord.display_name, dstRecord.display_name),
            confirm: () => {
                this.model.deleteDependencies([srcRecord.id], [dstRecord.id]);
            },
            cancel: () => {},
        });
    }

    onClickCreate() {
        const context = this.model.getDatesContext();
        this.openRecord({context: context});
    }

    /**
     * Opens dialog to add/edit/view a record
     *
     * @param {Record<string, any>} props FormViewDialog props
     * @param {Record<string, any>} [options={}]
     */
    openRecord(props, options = {}) {
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

    /**
     * Plan records
     *
     * @param {String} startDate
     * @param {String} endDate
     * @param {Object} extraData
     * @param {Object} extraContext
     **/
    planRecords(startDate, endDate, extraData, extraContext) {
        const domain = this.model.getPlanDialogDomain();
        const data =  Object.fromEntries(Object.entries(extraData).map(([k, v]) => [k, this.model.normalizeORMValueToWrite(k, v)]))

        const context = Object.assign(this.props.context, extraContext);

        // for the create button of the modal
        context[sprintf('default_%s', this.model.dateStartField)] = startDate;
        context[sprintf('default_%s', this.model.dateStopField)] = endDate;

        this.dialogService.add(
            SelectCreateDialog,
            {
                title: _t("Plan"),
                resModel: this.model.metaData.resModel,
                context: context,
                domain,
                noCreate: !this.model.canCreate,
                onSelected: (resIds) => {
                    if (resIds.length) {
                        this.model.reschedule(resIds, startDate, endDate, data);
                    }
                },
            }
        );
    }

}
