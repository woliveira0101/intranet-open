/* Detect-zoom
* -----------
* Cross Browser Zoom and Pixel Ratio Detector
* Version 1.0.4 | Apr 1 2013
* dual-licensed under the WTFPL and MIT license
* Maintained by https://github/tombigel
* Original developer https://github.com/yonran
*/
(function(root,ns,factory){"use strict";"undefined"!=typeof module&&module.exports?module.exports=factory(ns,root):"function"==typeof define&&define.amd?define(function(){return factory(ns,root)}):root[ns]=factory(ns,root)})(window,"detectZoom",function(){var devicePixelRatio=function(){return window.devicePixelRatio||1},fallback=function(){return{zoom:1,devicePxPerCssPx:1}},ie8=function(){var zoom=Math.round(100*(screen.deviceXDPI/screen.logicalXDPI))/100;return{zoom:zoom,devicePxPerCssPx:zoom*devicePixelRatio()}},ie10=function(){var zoom=Math.round(100*(document.documentElement.offsetHeight/window.innerHeight))/100;return{zoom:zoom,devicePxPerCssPx:zoom*devicePixelRatio()}},webkitMobile=function(){var deviceWidth=90==Math.abs(window.orientation)?screen.height:screen.width,zoom=deviceWidth/window.innerWidth;return{zoom:zoom,devicePxPerCssPx:zoom*devicePixelRatio()}},webkit=function(){var important=function(str){return str.replace(/;/g," !important;")},div=document.createElement("div");div.innerHTML="1<br>2<br>3<br>4<br>5<br>6<br>7<br>8<br>9<br>0",div.setAttribute("style",important("font: 100px/1em sans-serif; -webkit-text-size-adjust: none; text-size-adjust: none; height: auto; width: 1em; padding: 0; overflow: visible;"));var container=document.createElement("div");container.setAttribute("style",important("width:0; height:0; overflow:hidden; visibility:hidden; position: absolute;")),container.appendChild(div),document.body.appendChild(container);var zoom=1e3/div.clientHeight;return zoom=Math.round(100*zoom)/100,document.body.removeChild(container),{zoom:zoom,devicePxPerCssPx:zoom*devicePixelRatio()}},firefox4=function(){var zoom=mediaQueryBinarySearch("min--moz-device-pixel-ratio","",0,10,20,1e-4);return zoom=Math.round(100*zoom)/100,{zoom:zoom,devicePxPerCssPx:zoom}},firefox18=function(){return{zoom:firefox4().zoom,devicePxPerCssPx:devicePixelRatio()}},opera11=function(){var zoom=window.top.outerWidth/window.top.innerWidth;return zoom=Math.round(100*zoom)/100,{zoom:zoom,devicePxPerCssPx:zoom*devicePixelRatio()}},mediaQueryBinarySearch=function(property,unit,a,b,maxIter,epsilon){function binarySearch(a,b,maxIter){var mid=(a+b)/2;if(0>=maxIter||epsilon>b-a)return mid;var query="("+property+":"+mid+unit+")";return matchMedia(query).matches?binarySearch(mid,b,maxIter-1):binarySearch(a,mid,maxIter-1)}var matchMedia,head,style,div;window.matchMedia?matchMedia=window.matchMedia:(head=document.getElementsByTagName("head")[0],style=document.createElement("style"),head.appendChild(style),div=document.createElement("div"),div.className="mediaQueryBinarySearch",div.style.display="none",document.body.appendChild(div),matchMedia=function(query){style.sheet.insertRule("@media "+query+"{.mediaQueryBinarySearch "+"{text-decoration: underline} }",0);var matched="underline"==getComputedStyle(div,null).textDecoration;return style.sheet.deleteRule(0),{matches:matched}});var ratio=binarySearch(a,b,maxIter);return div&&(head.removeChild(style),document.body.removeChild(div)),ratio},detectFunction=function(){var func=fallback;return isNaN(screen.logicalXDPI)||isNaN(screen.systemXDPI)?window.navigator.msMaxTouchPoints?func=ie10:"orientation"in window&&"string"==typeof document.body.style.webkitMarquee?func=webkitMobile:"string"==typeof document.body.style.webkitMarquee?func=webkit:navigator.userAgent.indexOf("Opera")>=0?func=opera11:window.devicePixelRatio?func=firefox18:firefox4().zoom>.001&&(func=firefox4):func=ie8,func}();return{zoom:function(){return detectFunction().zoom},device:function(){return detectFunction().devicePxPerCssPx}}});


/*
 * scrollbarWidth - from http://chris-spittles.co.uk/?p=531
 */
function scrollbarWidth() {
    var $inner = jQuery('<div style="width: 100%; height:200px;">test</div>'),
        $outer = jQuery('<div style="width:200px;height:150px; position: absolute; top: 0; left: 0; visibility: hidden; overflow:hidden;"></div>').append($inner),
        inner = $inner[0],
        outer = $outer[0];
     
    jQuery('body').append(outer);
    var width1 = inner.offsetWidth;
    $outer.css('overflow', 'scroll');
    var width2 = outer.clientWidth;
    $outer.remove();
 
    return (width1 - width2);
}


/**
 * Scrolltable
 */
function scrollTablePrepare($table) {
    var $struct = $([ 
        '<div class="scrolltable">',
            '<div class="floaty placeholder">',
                '<table>',
                    '<thead></thead>',
                '</table>',
            '</div>',
            '<div class="floaty topHeader">',
                '<table>',
                    '<thead></thead>',
                '</table>',
            '</div>',
            '<div class="floaty leftHeader">',
                '<table>',
                    '<tbody></tbody>',
                '</table>',
            '</div>',
            '<div class="floaty data">',
                '<div class="scrollable">',
                    '<table>',
                        '<tbody></tbody>',
                    '</table>',
                '</div>',
            '</div>',
        '</div>'
    ].join('\n'));
    // classes and IDs
    $struct.addClass($table.attr('class')).attr('id', $table.attr('id'));
    $struct.find('table').addClass($table.attr('class')).attr('id', $table.attr('id'));
    $table.find('thead tr').each(function(){
        // placeholders
        var $row = $(this),
            $phRow = $('<tr/>').addClass($row.attr('class')).attr('id', $row.attr('id'));
        $row.find('th[data-scrolltable="placeholder"]').appendTo($phRow);
        $struct.find('.placeholder table thead').append($phRow);
        // top header
        $topRow = $('<tr/>').addClass($row.attr('class')).attr('id', $row.attr('id'));
        $row.find('th').appendTo($topRow);
        $struct.find('.topHeader table thead').append($topRow);
    });
    $table.find('tbody tr').each(function(){
        // left header
        var $row = $(this),
            $leftRow = $('<tr/>').addClass($row.attr('class')).attr('id', $row.attr('id'));
        $row.find('td[data-scrolltable="leftHeader"]').appendTo($leftRow);
        $struct.find('.leftHeader table tbody').append($leftRow);
        // normal cells
        $newRow = $('<tr/>').addClass($row.attr('class')).attr('id', $row.attr('id'));
        $row.find('td').appendTo($newRow);
        $struct.find('.data table tbody').append($newRow);
    });
    $table.replaceWith($struct);
}

/*
 * setSize sets size of all divs containing tables, to expand to the whole screen.
 */
function scrollTable($base) {
    $base.addClass('scrolltable');
    var $topParent = $base.find('.topHeader'),
        $leftParent = $base.find('.leftHeader'),
        $placeholder = $base.find('.placeholder'),
        $p = $base.find('.data'),
        $scrollable = $p.find('.scrollable'),
        $data = $p.find('table'),
        lastLeft = $scrollable.scrollLeft(),
        lastTop = $scrollable.scrollTop(),
        scrollWidth = scrollbarWidth();
    // Scroll event
    $scrollable.on('scroll', function(e){
        var left = $(this).scrollLeft(),
            top = $(this).scrollTop();
        // Do something only if values have changed
        if(left != lastLeft) {
            $topParent.scrollLeft(left);
            lastLeft = left;
        }
        if(top != lastTop) {
            $leftParent.scrollTop(top);
            lastTop = top;
        }
    });
    function setSize() {
            // Width: base width - userlist width
        var width = $base.innerWidth() - $leftParent.width(),
            // Height: window height - everything above base - dayslist
            height = $(window).innerHeight() - $base.offset().top - $topParent.height(), 
            // Margin compensates for scrollbars and bottom padding
            margin = detectZoom.zoom() * scrollWidth;
        $base.height(height);
        $placeholder.height($topParent.height());
        $placeholder.width($leftParent.width());

        $leftParent.css('top', $topParent.height()+'px');
        if($data.width() < width) { // Do we need horizontal scrollbar?
            $leftParent.css('bottom', '0');
            $p.css('width', ($data.width()+margin+1)+'px');
        } else {
            $leftParent.css('bottom', margin+'px');
        }
        $topParent.css('left', $leftParent.width()+'px');
        if($data.height() < height) { // Do we need vertical scrollbar?
            $topParent.css('right', '0');
            var newHeight = $data.height()+margin+1;
            $p.css('height', newHeight+'px');
            $base.height(newHeight+$topParent.height());
        } else {
            $topParent.css('right', margin+'px');
        }
        // $p is bigger to recompensate for scrollbars
        $p.css({
            top: $topParent.height()+'px',
            left: $leftParent.width()+'px'
        });
        $scrollable.height($p.height());
    }
    $(window).resize(function(e){
        setSize();
    });
    setTimeout(setSize, 10);
}
