/** @odoo-module */

import { deserializeDate, deserializeDateTime, formatDateTime, serializeDate, serializeDateTime } from "@web/core/l10n/dates";
import { Domain } from "@web/core/domain";
import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { x2ManyCommands } from "@web/core/orm_service";
import { unique } from "@web/core/utils/arrays";
import { KeepLast, Mutex } from "@web/core/utils/concurrency";
import { sprintf } from "@web/core/utils/strings";
import { Model } from "@web/views/model";

const { DateTime, Settings } = luxon;


import { status, useComponent, useEffect, useRef, onWillDestroy } from "@odoo/owl";
/**
 * Returns start and end dates of the given scale (included), in local timezone.
 *
 * @param {ScaleId} scale
 * @param {DateTime} date DateTime object, in local timezone
 */
const computeRange = function(scale, date) {
    let start = date;
    let end = date;

    if (scale === "week") {
        // startOf("week") does not depend on locale and will always give the
        // "Monday" of the week... (ISO standard)
        const { weekStart } = localization;
        const weekday = start.weekday < weekStart ? weekStart - 7 : weekStart;
        start = start.set({ weekday }).startOf("day");
        end = start.plus({ weeks: 1, days: -1 }).endOf("day");
    } else {
        start = start.startOf(scale);
        end = end.endOf(scale);
    }

    return { start, end };
}


export class GanttModel extends Model {
    setup(params, services) {
        this.dateStartField = params.archInfo.dateStartField;
        this.dateStopField = params.archInfo.dateStopField;
        this.colorField = params.archInfo.colorField;
        this.progressField = params.archInfo.progressField;

        this.initialGroupBy = params.archInfo.defaultGroupBy;
        this.initialOrderBy = params.archInfo.defaultOrderBy;
        this.initialScaleId = params.archInfo.defaultScale;

        this.allowedScales = params.archInfo.scales || {};
        this.groupLimit = params.archInfo.limit || 80;

        this.fieldInfos = params.fields;
        this.fieldsToFetch = params.archInfo.fieldNames;

        this.metaData = params;
        this.data = null;
        this.searchParams = null;

        /** @type {Data} */
        this.groupTree = [];
        this.recordMap = {};

        // concurrency management
        this.keepLast = new KeepLast();
        this.mutex = new Mutex();
    }

    async load(params = {}) {
        if(!this.metaData.focusDate) {
            this.metaData.focusDate = params.context && params.context.initial_date
                ? deserializeDateTime(params.context.initial_date)
                : luxon.DateTime.local();
        }
        if(!this.metaData.groupBy) {
            this.metaData.groupBy = this.initialGroupBy;
        }
        if(!this.metaData.scale) {
            this.metaData.scale = this.allowedScales[this.initialScaleId];
            params.scaleId = this.metaData.scale.id; // trigger the compute range
        }
        if(!this.metaData.pagerOffset) {
            this.metaData.pagerOffset = 0;
        }

        const metaData = this._buildMetaData(params);
        await this.keepLast.add(this._loadData(metaData));

        this.metaData = metaData;
        this.notify();
    }

    /**
     * Reschedule a task to the given schedule.
     *
     * @param {number | number[]} ids
     * @param {String} startDate: server format date
     * @param {String} stopDate: server format date
     * @param {(result: any) => any} [callback]
     */
    async reschedule(ids, startDate, stopDate, callback) {
        if (!Array.isArray(ids)) {
            ids = [ids];
        }
        const data = {};
        data[this.dateStartField] = startDate;
        data[this.dateStopField] = stopDate;

        const context = this.metaData.context;
        return this.mutex.exec(async () => {
            try {
                const result = await this.orm.write(this.metaData.resModel, ids, data, {
                    context,
                });
            } finally {
                await this.load();
            }
        });
    }

    async updateProgress(ids, progress) {
        if (!Array.isArray(ids)) {
            ids = [ids];
        }
        const data = {};
        data[this.progressField] = progress;

        const context = this.metaData.context;
        return this.mutex.exec(async () => {
            try {
                const result = await this.orm.write(this.metaData.resModel, ids, data, {
                    context,
                });
            } finally {
                await this.load();
            }
        });
    }

    get useDateOnly() {
        return this.fieldInfos[this.dateStartField].type == 'date';
    }

    //-------------------------------------------------------------------------
    // Private
    //-------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} params
     * @param {string[]} [params.groupBy]
     * @param {Array} [params.domain]
     * @param {Object} [params.context]
     * @param {DateTime} [params.focusDate]
     * @param {ScaleId} [params.scaleId]
     * @returns {metaData}
     */
    _buildMetaData(params = {}) {
        const metaData = Object.assign({}, this.metaData, params);

        // Search View
        if (params.groupBy) {
            if (params.groupBy && params.groupBy.length) {
                metaData.groupBy = params.groupBy.filter(
                    groupedByField => {
                        var fieldName = groupedByField.split(':')[0]
                        return fieldName in metaData.fields && metaData.fields[fieldName].type.indexOf('date') === -1;
                    }
                );
                if(metaData.groupBy.length !== params.groupBy.length){
                    this.do_warn(_t('Invalid group by'), _t('Grouping by date is not supported, ignoring it'));
                }
            } else {
                metaData.groupBy = this.initialGroupBy;
            }
        }

        // Gantt Time Scale
        let recomputeRange = false;
        if (params.scaleId) {
            metaData.scale = this.allowedScales[params.scaleId];
            recomputeRange = true;
        }
        if (params.focusDate) {
            metaData.focusDate = params.focusDate;
            recomputeRange = true;
        }

        if (recomputeRange) {
            const { start, end } = computeRange(metaData.scale.id, metaData.focusDate);
            metaData.startDate = start;
            metaData.stopDate = end;
        }

        // Reset Offset
        const resetOffset = Object.keys(params).some(k => k in ['groupBy', 'scaleId', 'focusDate', 'domain']);
        if (resetOffset) {
            metaData.pagerOffset = 0;
        }
        return metaData;
    }

    /**
     * @private
     * @returns {Deferred<any>}
     */
    async _fetchGanttData (metaData) {
        const { groupBy, pagerOffset, resModel } = metaData;
        const context = {
            ...metaData.context || {},
            group_by: groupBy,
        };
        const domain = this._getDomain(metaData);
        const fields = this._getFields(metaData);

        const { length, groups, records } = await this.orm.call(resModel, "gantt_read", [], {
                domain,
                fields: fields,
                groupby: groupBy,
                offset: pagerOffset,
                limit: this.groupLimit,
                orderby: this.initialOrderBy || null,
                context,
            })
        ;
        return { length, groups, records };
    }


    /**
     * Return a Tree of group hierachy based on the group by path.
     * @param {string[]} groupedBy: list of group by field names
     * @param {object[]} groups: group data from the server
     * @param {string} parentGroupId: Identifier of the parent group
     * @param {Object} parentDefaultContext: context containing the default value for record created in this group.
     */
    _generateTreeGroup(groupedBy, groups, parentGroupId, parentDefaultContext){
        let nodes = [];

        if (groupedBy.length) {
            const headGroupBy = groupedBy[0];
            const tailGroupBy = groupedBy.slice(1);

            const currentLevelGroups = _.groupBy(groups, headGroupBy);

            for (const [groupBy, subGroups] of Object.entries(currentLevelGroups)) {
                const headGroupValue = subGroups[0][headGroupBy]; // we are sure there is at least one elem otherwise the group wouldn't exist.
                // context with default value coming from the group
                let defaultContext = {};
                if (parentDefaultContext){
                    defaultContext = parentDefaultContext;
                }
                defaultContext[sprintf("default_%s", headGroupBy)] = this._normalizeContextValue(headGroupBy, headGroupValue);
                // group record IDs
                const recordIds = [];
                for (const g of subGroups) {
                    recordIds.push(...(g.__record_ids || []));
                }
                // row struct
                const groupId = _.uniqueId('group');
                const node = {
                    groupId,
                    parentGroupId,
                    name: this._getGroupName(headGroupBy, headGroupValue),
                    recordIds,
                    childNodes: this._generateTreeGroup(tailGroupBy, subGroups, groupId, {...defaultContext}),
                    isGroup: true,
                    context: {...defaultContext},
                }
                nodes.push(node);
            }
        } else {
            // group record IDs
            const recordIds = [];
            for (const g of groups) {
                recordIds.push(...(g.__record_ids || []));
            }
            // row struct
            const groupId = _.uniqueId('group');
            const node = {
                groupId,
                parentGroupId,
                name: null,
                recordIds,
                childNodes: null,
                isGroup: false,
                context: {...parentDefaultContext},
            }
            nodes = [node];
        }

        return nodes;
    }


    /**
     * Get domain of records to display in the gantt view.
     *
     * @private
     * @param {metaData} metaData
     * @returns {Array[]}
     */
    _getDomain(metaData) {
        const serializerFunc = this.useDateOnly ? serializeDate : serializeDateTime;
        const baseDomain = metaData.domain || [];
        const gantDomain = [
            "&",
            [this.dateStartField, '<=', serializerFunc(metaData.stopDate)],
            [this.dateStopField, '>=', serializerFunc(metaData.startDate)],
        ];
        return Domain.and([baseDomain, gantDomain]).toList();
    }

    /**
     * Get all the fields needed.
     *
     * @private
     * @returns {string[]}
     */
    _getFields() {
        let fields = ['display_name', this.dateStartField, this.dateStopField];
        fields = fields.concat(this.metaData.groupBy);

        if (this.colorField) {
            fields.push(this.colorField);
        }
        if (this.progressField) {
            fields.push(this.progressField);
        }
        if (this.fieldsToFetch){
            fields = fields.concat(this.fieldsToFetch);
        }
        return unique(fields);
    }

    _getGroupName(fieldName, value) {
        const field = this.fieldInfos[fieldName];
        if (field.type === "boolean") {
            return value ? "True" : "False";
        } else if (!value) {
            return _t("Undefined %s", field.string);
        } else if (field.type === "many2many") {
            return value[1];
        }
        const formatter = registry.category("formatters").get(field.type);
        return formatter(value, field);
    }

    async _loadData(metaData){
        const { length, groups, records } = await this._fetchGanttData(metaData);

        const parsedRecords = this._parseServerData(metaData, records);
        const recordMap = {};
        for (const record of parsedRecords) {
            recordMap[record.id] = record;
        }
        this.recordMap = recordMap;
        this.groupTree = this._generateTreeGroup(metaData.groupBy, groups, null, metaData.context);  // requires the action context
    }

    _normalizeContextValue(fieldName, value) {
        const fieldInfo = this.fieldInfos[fieldName];
        switch (fieldInfo.type) {
            case "many2one":
                if (value){
                    value = value[0];
                }
                break;
            case "many2many": // this is the same as M2O
                if (value) {
                    return [[6, 0, [value[0]]]];
                }
                break;
            default:
                // keep given value
            }
        return value;
    }

    /**
     * @private
     * @param {MetaData} metaData
     * @param {Record<string, any>[]} records the server records to parse
     * @returns {Record<string, any>[]}
     */
    _parseServerData(metaData, records) {
        const {
            startDate,
            stopDate,
            fields,
        } = metaData;
        /** @type {Record<string, any>[]} */
        const parsedRecords = [];
        for (const record of records) {
            const parsedRecord = this._parseServerValues(metaData.fields, record);
            const dateStart = parsedRecord[this.dateStartField];
            const dateStop = parsedRecord[this.dateStopField];
            if (dateStart <= dateStop) {
                parsedRecords.push(parsedRecord);
            }
        }
        return parsedRecords;
    }

    /**
     * @private
     * @param {fieldInfos} fields
     * @param {Record<string, any>[]} values:  server records to parse
     * @returns {Record<string, any>[]}
     */
    _parseServerValues(fields, values) {
        const parsedValues = {};
        if (!values) {
            return parsedValues;
        }
        for (const fieldName in values) {
            const field = fields[fieldName];
            const value = values[fieldName];
            switch (field.type) {
                case "date": {
                    parsedValues[fieldName] = value ? deserializeDate(value) : false;
                    break;
                }
                case "datetime": {
                    parsedValues[fieldName] = value ? deserializeDateTime(value) : false;
                    break;
                }
                case "selection": {
                    if (value === false) {
                        // process selection: convert false to 0, if 0 is a valid key
                        const hasKey0 = field.selection.some((option) => option[0] === 0);
                        parsedValues[fieldName] = hasKey0 ? 0 : value;
                    } else {
                        parsedValues[fieldName] = value;
                    }
                    break;
                }
                /*case "many2one": {
                    parsedValues[fieldName] = value ? [value.id, value.display_name] : false;
                    break;
                }*/
                default: {
                    parsedValues[fieldName] = value;
                }
            }
        }
        return parsedValues;
    }

}