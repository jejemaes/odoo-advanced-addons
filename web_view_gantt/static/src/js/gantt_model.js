odoo.define('web_view_gantt.GanttModel', function (require) {
"use strict";

var AbstractModel = require('web.AbstractModel');
var concurrency = require('web.concurrency');
var session = require('web.session');
var GanttUtils = require('web_view_gantt.GanttUtils');
var core = require('web.core');

var _t = core._t;


return AbstractModel.extend({

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.gantt = null;

        this.dp = new concurrency.DropPrevious();
        this.mutex = new concurrency.Mutex();
        this._ganttInfo = {};
        this._ganttRows = {}; // map row id --> row object (see generateRows)
        this.useDateOnly = null;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @returns {Object}
     */
    get: function () {
        return _.extend({}, this._ganttInfo);
    },
    getRowContext: function (rowId) {
        var row = this._ganttRows[rowId];
        if (row) {
            return row.context;
        }
        return {};
    },
    /**
     * Load gantt data
     *
     * @param {Object} params
     * @returns {Deferred<any>}
     */
    load: function (params) {
        this.modelName = params.modelName;
        this.fields = params.fields;
        this.domain = params.domain;
        this.context = params.context;
        this.colorField = params.colorField;
        this.progressField = params.progressField;
        this.decorationFields = params.decorationFields;
        this.useDateOnly = params.useDateOnly;
        // this.displayUnavailability = params.displayUnavailability;

        this.defaultGroupBy = params.defaultGroupBy ? [params.defaultGroupBy] : [];
        if (!params.groupedBy || !params.groupedBy.length) {
            params.groupedBy = this.defaultGroupBy;
        }

        this._ganttInfo = {
            dateStartField: params.dateStartField,
            dateStopField: params.dateStopField,
            groupedBy: params.groupedBy,
            fields: params.fields,
        };
        this._ganttRows = {};

        this._setFocusDate(params.initialDate, params.scale);
        return this._fetchGanttData();
    },
    /**
     * Update dates of given tasks
     * @param {Object} schedule
     */
    reschedule: function (ids, schedule) {
        var self = this;
        if (!_.isArray(ids)) {
            ids = [ids];
        }

        var allowedFields = [
            this._ganttInfo.dateStartField,
            this._ganttInfo.dateStopField,
        ];

        var data = _.pick(schedule, allowedFields);
        Object.keys(data).forEach(function(key) {
            data[key] = GanttUtils.dateToServer(data[key], self.useDateOnly);
        });

        return this.mutex.exec(function () {
            return self._rpc({
                model: self.modelName,
                method: 'write',
                args: [ids, data],
                context: self.context,
            });
        });
    },
    /**
     * Same as 'load'
     *
     * @returns {Deferred<any>}
     */
    reload: function (handle, params) {
        if ('scale' in params) {
            this._setFocusDate(this._ganttInfo.focusDate, params.scale);
        }
        if ('date' in params) {
            this._setFocusDate(params.date, this._ganttInfo.scale);
        }
        if ('domain' in params) {
            this.domain = params.domain;
        }
        if ('groupBy' in params) {
            if (params.groupBy && params.groupBy.length) {
                this._ganttInfo.groupedBy = params.groupBy.filter(
                    groupedByField => {
                        var fieldName = groupedByField.split(':')[0]
                        return fieldName in this.fields && this.fields[fieldName].type.indexOf('date') === -1;
                    }
                );
                if(this._ganttInfo.groupedBy.length !== params.groupBy.length){
                    this.do_warn(_t('Invalid group by'), _t('Grouping by date is not supported, ignoring it'));
                }
            } else {
                this._ganttInfo.groupedBy = this.defaultGroupBy;
            }
        }
        return this._fetchGanttData();
    },
    /**
     * @param {Moment} focusDate
     */
    setFocusDate: function (focusDate) {
        this._setFocusDate(focusDate, this._ganttInfo.scale);
    },
    /**
     * @param {string} scale
     */
    setScale: function (scale) {
        this._setFocusDate(this._ganttInfo.focusDate, scale);
    },
    /**
     * Save the progress (percentage) field value for the given ids
     *
     * @param {array} ids
     * @param {float} progress
     */
    changeProgress: function (ids, progress) {
        if (!_.isArray(ids)) {
            ids = [ids];
        }
        var values = {};
        values[this.progressField] = Math.round(progress * 10) / 10;
        return this._rpc({
            model: this.modelName,
            method: 'write',
            args: [ids, values],
            context: this.context,
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Get domain of records to display in the gantt view.
     *
     * @private
     * @returns {Array[]}
     */
    _getDomain: function () {
        var domain = [
            [this._ganttInfo.dateStartField, '<=', GanttUtils.dateToServer(this._ganttInfo.stopDate, this.useDateOnly)],
            [this._ganttInfo.dateStopField, '>=', GanttUtils.dateToServer(this._ganttInfo.startDate, this.useDateOnly)],
        ];
        return this.domain.concat(domain);
    },
    /**
     * Get all the fields needed.
     *
     * @private
     * @returns {string[]}
     */
    _getFields: function () {
        var fields = ['display_name', this._ganttInfo.dateStartField, this._ganttInfo.dateStopField];
        fields = fields.concat(this._ganttInfo.groupedBy, this.decorationFields || []);
        if (this.progressField) {
            fields.push(this.progressField);
        }
        if (this.colorField) {
            fields.push(this.colorField);
        }
        return _.uniq(fields);
    },
    /**
     * @private
     * @returns {Deferred<any>}
     */
    _fetchGanttData: function () {
        var self = this;
        var domain = this._getDomain();
        var context = _.extend(this.context, {'group_by': this._ganttInfo.groupedBy});

        var groupsDef;
        if (this._ganttInfo.groupedBy.length) {
            groupsDef = this._rpc({
                model: this.modelName,
                method: 'read_group',
                fields: this._getFields(),
                domain: domain,
                context: context,
                groupBy: this._ganttInfo.groupedBy,
                lazy: this._ganttInfo.groupedBy.length === 1,
            });
        }

        var dataDef = this._rpc({
            route: '/web/dataset/search_read',
            model: this.modelName,
            fields: this._getFields(),
            context: context,
            domain: domain,
        });

        return this.dp.add(Promise.all([groupsDef, dataDef])).then(function (results) {
            var groups = results[0];
            var searchReadResult = results[1];

            var records = self._parseServerData(searchReadResult.records);
            self._ganttInfo.data = records;
            self._ganttInfo.rows = self._generateRows(self._ganttInfo.groupedBy, groups, records);
        });
    },

    _generateRows: function (groupedBy, groups, records, parentParams) {
        var self = this;
        var rows = [];

        var parentParams = parentParams || {};
        var parentRowId = parentParams.rowId;
        var parentValues = parentParams.data;

        if (groupedBy.length) {
            var currentGroupedByField = groupedBy[0];
            var currentLevelGroups = _.groupBy(groups, currentGroupedByField);

            Object.keys(currentLevelGroups).forEach(function(groupValue) {
                var subGroups = currentLevelGroups[groupValue];
                var groupValue = subGroups[0][currentGroupedByField];

                var groupRecords = _.filter(records, function (record) {
                    return _.isEqual(record[currentGroupedByField], groupValue);
                });

                // For empty groups, we can't look at the record to get the
                // formatted value of the field, we have to trust expand_groups
                var value;
                if (groupRecords.length) {
                    value = groupRecords[0][currentGroupedByField];
                } else {
                    value = groupValue;
                }

                // value of the group row (used as default value later)
                var data = parentValues ? _.clone(parentValues) : {};
                data[currentGroupedByField] = _.isArray(value) ? value[0] : value;

                var rowId = _.uniqueId('row');
                var row = {
                    id: rowId,
                    parentId: parentRowId,
                    name: GanttUtils.formatFieldValue(value, self.fields[currentGroupedByField]),
                    groupedBy: groupedBy,
                    groupedByField: currentGroupedByField,
                    resId: _.isArray(value) ? value[0] : value,
                    rows: self._generateRows(groupedBy.slice(1), subGroups, groupRecords,{'rowId': rowId, 'data': data}),
                    data: data,
                };
                self._ganttRows[rowId] = row;

                rows.push(row);
            });
        } else {
            var rowId = _.uniqueId('row');
            var row = {
                id: rowId,
                parentId: parentRowId,
                records: records,
                data: parentValues,
            };
            rows = [row];
            self._ganttRows[rowId] = row;
        }
        return rows;
    },
    /**
     * Parse in place the server values (and in particular, convert datetime
     * field values to moment in UTC).
     *
     * @private
     * @param {Object} data the server data to parse
     * @returns {Promise<any>}
     */
    _parseServerData: function (data) {
        var self = this;

        data.forEach(function (record) {
            Object.keys(record).forEach(function (fieldName) {
                record[fieldName] = self._parseServerValue(self.fields[fieldName], record[fieldName]);
            });
        });
        return data;
    },
    /**
     * @private
     * @param {any} focusDate
     * @param {string} scale
     */
    _setFocusDate: function (focusDate, scale) {
        this._ganttInfo.scale = scale;
        this._ganttInfo.focusDate = focusDate;
        this._ganttInfo.startDate = focusDate.clone().startOf(scale);
        this._ganttInfo.stopDate = focusDate.clone().endOf(scale);
    },
});

});
