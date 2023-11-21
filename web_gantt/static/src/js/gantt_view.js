/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { GanttController } from "./gantt_controller";
import { GanttArchParser } from "./gantt_arch_parser";
import { GanttModel } from "./gantt_model";
import { GanttRenderer } from "./gantt_renderer";


export const GanttView = {
    type: "gantt",
    display_name: _t("Gantt"),
    icon: "fa fa-tasks",
    isMobileFriendly: false,
    multiRecord: true,

    ArchParser: GanttArchParser,
    Controller: GanttController,
    Model: GanttModel,
    Renderer: GanttRenderer,
    buttonTemplate: "web_gantt.GanttController.ControlButtons",

    props(genericProps, view, config) {
        const { ArchParser } = view;
        const { arch, relatedModels, resModel } = genericProps;
        const archInfo = new ArchParser().parse(arch, relatedModels, resModel);

        let formViewId = archInfo.formViewId;
        if (!formViewId) {
            const formView = config.views.find((v) => v[1] === "form");
            if (formView) {
                formViewId = formView[0];
            }
        }

        return {
            ...genericProps,
            Model: view.Model,
            Renderer: view.Renderer,
            buttonTemplate: view.buttonTemplate,
            archInfo,
            formViewId,
        };
    },
};

registry.category("views").add("gantt", GanttView);
