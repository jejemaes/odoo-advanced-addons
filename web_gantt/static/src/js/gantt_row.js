odoo.define('web_gantt.GanttRow', function (require) {
"use strict";

var Widget = require('web.Widget');

var GanttRow = Widget.extend({
    template: 'GanttView.Row',
    // empty class for compatibility with module extending the gantt view (entreprise module)
});

return GanttRow;

});
