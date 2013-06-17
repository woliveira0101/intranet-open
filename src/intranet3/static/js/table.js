function scrollTablePrepare($table) {
    
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
        if($data.height() < height) { // Do we need scrollbars?
            $topParent.width(width);
            height = $data.height() + margin;
        } else {
            $topParent.width(width-margin);
            height = height - 2*margin;
        }
        $leftParent.height(height-margin);
        // $p is bigger to recompensate for scrollbars
        $p.width(width).height(height);
    }
    $(window).resize(function(e){
        setSize();
    });
    setSize();
}
