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
