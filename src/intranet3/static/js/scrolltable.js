function scrollTablePrepare($table) {
    var $struct = $([ 
        '<div class="scrolltable">',
            '<div class="holder">',
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
            '</div>',
            '<div class="clear"><!-- nothing --></div>',
            '<div class="holder">',
                '<div class="floaty leftHeader">',
                    '<table>',
                        '<tbody></tbody>',
                    '</table>',
                '</div>',
                '<div class="floaty scrollable">',
                    '<table>',
                        '<tbody></tbody>',
                    '</table>',
                '</div>',
            '</div>',
        '</div>'
    ].join('\n'));
    // classes and IDs
    $struct.find('table').addClass($table.attr('class')).attr('id', $table.attr('id'));
    $table.find('thead tr').each(function(){
        // placeholders
        var $row = $(this),
            $phRow = $('<tr/>');
        $row.find('th[data-scrolltable="placeholder"]').appendTo($phRow);
        $struct.find('.placeholder table thead').append($phRow);
        // top header
        $topRow = $('<tr/>');
        $row.find('th').appendTo($topRow);
        $struct.find('.topHeader table thead').append($topRow);
    });
    $table.find('tbody tr').each(function(){
        // left header
        var $row = $(this),
            $leftRow = $('<tr/>');
        $row.find('td[data-scrolltable="leftHeader"]').appendTo($leftRow);
        $struct.find('.leftHeader table tbody').append($leftRow);
        // normal cells
        $newRow = $('<tr/>');
        $row.find('td').appendTo($newRow);
        $struct.find('.scrollable table tbody').append($newRow);
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
        $p = $base.find('.scrollable'),
        $data = $p.find('table');
        lastLeft = $p.scrollLeft(),
        lastTop = $p.scrollTop();
    // Scroll event
    $p.on('scroll', function(e){
        var left = $p.scrollLeft(),
            top = $p.scrollTop();
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
            margin = 15;
        $placeholder.height($topParent.height());
        $placeholder.width($leftParent.width());
        if($data.height() < height) { // Do we need vertical scrollbar?
            $topParent.width(width);
            height = $data.height() + margin;
        } else {
            $topParent.width(width-margin);
            height = height - 2*margin;
        }
        if($data.width() < width) { // Do we need horizontal scrollbar?
            $leftParent.height(height);
        } else {
            $leftParent.height(height-margin);
        }
        // $p is bigger to recompensate for scrollbars
        $p.width(width).height(height);
    }
    $(window).resize(function(e){
        setSize();
    });
    setSize();
}
