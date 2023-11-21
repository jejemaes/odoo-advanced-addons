/** @odoo-module **/

import {
    addFieldDependencies,
    archParseBoolean,
    getActiveActions,
    stringToOrderBy,
} from "@web/views/utils";
import { extractAttributes, XMLParser } from "@web/core/utils/xml";
import { Field } from "@web/views/fields/field";
import { Widget } from "@web/views/widgets/widget";
import { _t } from "@web/core/l10n/translation";
import { evaluateExpr } from "@web/core/py_js/py";

/**
 * @typedef scale
 * @property {string} id (`day`, `week`, `month`, `year`)
 * @property {string} description
 * @property {string} cellPrecision (`quarter`, `half`, `full`)
 * @property {string} cellUnit (`hour`, `day`, `week`, `month`)
 */

const DECORATIONS = [
    "decoration-danger",
    "decoration-success",
    "decoration-warning",
];
export const SCALES = {
    day: {
        description: _t("Day"),
        allowedUnitPrecision: {
            hour: ['full', 'half', 'quarter']
        },
        defaultPrecision: "full",
        defaultUnit: "hour",
    },
    week: {
        description: _t("Week"),
        allowedUnitPrecision: {
            hour: ['full'],
            day: ['full', 'half']
        },
        defaultPrecision: "half",
        defaultUnit: "day",
    },
    month: {
        description: _t("Month"),
        allowedUnitPrecision: {
            day: ['full'],
            week: ['full']
        },
        defaultPrecision: "full",
        defaultUnit: "day",
    },
    year: {
        description: _t("Year"),
        allowedUnitPrecision: {
            week: ['full'],
            month: ['full']
        },
        defaultPrecision: "full",
        defaultUnit: "month",
    },
};

export class GanttArchParser extends XMLParser {
    parse(arch, models, modelName) {
        const fields = models[modelName];
        const fieldNames = [];
        let jsClass = null;
        let ganttRootAttrs = {};

        this.visitXML(arch, (node) => {
            switch (node.tagName) {
                case "gantt": {
                    jsClass = node.getAttribute("js_class");  // need to be fill when exploring <field> nodes
                    ganttRootAttrs = this.visitGantt(node);
                    break;
                }
                case "field": {
                    const fieldName = node.getAttribute("name");
                    fieldNames.push(fieldName);
                    const fieldInfo = Field.parseFieldNode(
                        node,
                        models,
                        modelName,
                        "gantt",
                        jsClass
                    );
                    break;
                }
            }
        });

        return {
            ...ganttRootAttrs,
            fieldNames: [...fieldNames],
        }

    }

    visitGantt(xmlDoc){
        const className = xmlDoc.getAttribute("class") || null;
        const viewTitle = xmlDoc.getAttribute("string") || null;

        const jsClass = xmlDoc.getAttribute("js_class");
        const defaultGroupBy = xmlDoc.getAttribute("default_group_by") ? xmlDoc.getAttribute("default_group_by").split(",") : [];
        const defaultOrderBy = stringToOrderBy(xmlDoc.getAttribute("default_order_by")) || ['id'];
        const defaultScale = xmlDoc.getAttribute("default_scale") || "month";
        const dateStartField = xmlDoc.getAttribute("date_start");
        const dateStopField = xmlDoc.getAttribute("date_stop");
        const colorField = xmlDoc.getAttribute("color");
        const limit = xmlDoc.getAttribute("limit") || 80;
        const progressField = xmlDoc.getAttribute("progress") || null;

        // scales
        const scaleAttr = xmlDoc.getAttribute("scales");
        let allowedScales;
        if (scaleAttr) {
            allowedScales = [];
            for (const key of scaleAttr.split(",")) {
                if (SCALES[key]) {
                    allowedScales.push(key);
                }
            }
        } else {
            allowedScales = Object.keys(SCALES);
        }

        // precision = {'day': 'hour:half', 'week': 'day:half', 'month': 'day', 'year': 'month:quarter'}
        const precision = xmlDoc.getAttribute("precision");
        const precisionAttrs = precision ? evaluateExpr(precision) : {};

        const allowedScaleInfos = {};
        for (const scaleId of allowedScales) {

            const scale = {
                id: scaleId,
                description: SCALES[scaleId].description,
                cellPrecision: SCALES[scaleId].defaultPrecision,
                cellUnit: SCALES[scaleId].defaultUnit,
            };

            if (precisionAttrs[scaleId]){
                const unitPrecision = precisionAttrs[scaleId].split(":"); // hour:half
                const unit = unitPrecision[0];
                const precision = unitPrecision[1];
                if(SCALES[scaleId].allowedUnitPrecision[unit]) {
                    scale.cellUnit = unit;
                }
                if(SCALES[scaleId].allowedUnitPrecision[scale.cellUnit].includes(precision)) {
                    scale.cellPrecision = precision;
                }
            }
            allowedScaleInfos[scaleId] = scale;
        }

        const decorationMap = {};
        for (const decoration of DECORATIONS) {
            const decorationExpr = xmlDoc.getAttribute(decoration)
            if (decorationExpr) {
                decorationMap[decoration] = decorationExpr;
            }
        }

        return {
            activeActions: getActiveActions(xmlDoc),
            className,
            colorField,
            decorationMap,
            dateStartField,
            dateStopField,
            defaultGroupBy,
            defaultOrderBy,
            defaultScale,
            limit: limit && parseInt(limit, 10),
            scales: allowedScaleInfos,
            viewTitle,
            progressField,
        };
    }
}
