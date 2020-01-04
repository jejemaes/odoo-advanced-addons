/*
@license

dhtmlxGantt v.6.3.4 Standard

This version of dhtmlxGantt is distributed under GPL 2.0 license and can be legally used in GPL projects.

To use dhtmlxGantt in non-GPL projects (and get Pro version of the product), please obtain Commercial/Enterprise or Ultimate license on our site https://dhtmlx.com/docs/products/dhtmlxGantt/#licensing or contact us at sales@dhtmlx.com

(c) XB Software Ltd.

*/
!function(t,e){"object"==typeof exports&&"object"==typeof module?module.exports=e():"function"==typeof define&&define.amd?define("ext/dhtmlxgantt_marker",[],e):"object"==typeof exports?exports["ext/dhtmlxgantt_marker"]=e():t["ext/dhtmlxgantt_marker"]=e()}(window,function(){return function(t){var e={};function r(a){if(e[a])return e[a].exports;var n=e[a]={i:a,l:!1,exports:{}};return t[a].call(n.exports,n,n.exports,r),n.l=!0,n.exports}return r.m=t,r.c=e,r.d=function(t,e,a){r.o(t,e)||Object.defineProperty(t,e,{enumerable:!0,get:a})},r.r=function(t){"undefined"!=typeof Symbol&&Symbol.toStringTag&&Object.defineProperty(t,Symbol.toStringTag,{value:"Module"}),Object.defineProperty(t,"__esModule",{value:!0})},r.t=function(t,e){if(1&e&&(t=r(t)),8&e)return t;if(4&e&&"object"==typeof t&&t&&t.__esModule)return t;var a=Object.create(null);if(r.r(a),Object.defineProperty(a,"default",{enumerable:!0,value:t}),2&e&&"string"!=typeof t)for(var n in t)r.d(a,n,function(e){return t[e]}.bind(null,n));return a},r.n=function(t){var e=t&&t.__esModule?function(){return t.default}:function(){return t};return r.d(e,"a",e),e},r.o=function(t,e){return Object.prototype.hasOwnProperty.call(t,e)},r.p="/codebase/",r(r.s=227)}({227:function(t,e){!function(){function t(t){if(!gantt.config.show_markers)return!1;if(!t.start_date)return!1;var e=gantt.getState();if(!(+t.start_date>+e.max_date||(!t.end_date||+t.end_date<+e.min_date)&&+t.start_date<+e.min_date)){var r=document.createElement("div");r.setAttribute("data-marker-id",t.id);var a="gantt_marker";gantt.templates.marker_class&&(a+=" "+gantt.templates.marker_class(t)),t.css&&(a+=" "+t.css),t.title&&(r.title=t.title),r.className=a;var n=gantt.posFromDate(t.start_date);if(r.style.left=n+"px",r.style.height=Math.max(gantt.getRowTop(gantt.getVisibleTaskCount()),0)+"px",t.end_date){var o=gantt.posFromDate(t.end_date);r.style.width=Math.max(o-n,0)+"px"}return t.text&&(r.innerHTML="<div class='gantt_marker_content' >"+t.text+"</div>"),r}}function e(){if(gantt.$task_data){var t=document.createElement("div");t.className="gantt_marker_area",gantt.$task_data.appendChild(t),gantt.$marker_area=t}}gantt._markers||(gantt._markers=gantt.createDatastore({name:"marker",initItem:function(t){return t.id=t.id||gantt.uid(),t}})),gantt.config.show_markers=!0,gantt.attachEvent("onBeforeGanttRender",function(){gantt.$marker_area||e()}),gantt.attachEvent("onDataRender",function(){gantt.$marker_area||(e(),gantt.renderMarkers())}),gantt.attachEvent("onGanttReady",function(){e(),gantt.$services.getService("layers").createDataRender({name:"marker",defaultContainer:function(){return gantt.$marker_area}}).addLayer(t)}),gantt.getMarker=function(t){return this._markers?this._markers.getItem(t):null},gantt.addMarker=function(t){return this._markers.addItem(t)},gantt.deleteMarker=function(t){return!!this._markers.exists(t)&&(this._markers.removeItem(t),!0)},gantt.updateMarker=function(t){this._markers.refresh(t)},gantt._getMarkers=function(){return this._markers.getItems()},gantt.renderMarkers=function(){this._markers.refresh()}}()}})});
//# sourceMappingURL=dhtmlxgantt_marker.js.map