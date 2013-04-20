(function($){
    var TIMEOUT = 5 * 60 * 1000;
    
    function log(msg) {
        try {
            console.log(msg);
        } catch(e) {
            // ignore
        }
    }
    
    function resize(){
        if(typeof gadgets !== "undefined"){
            gadgets.window.adjustHeight();
        }
    }

    $(window).load(function(){
        /* if opened from calendar, set gadget height to enforce scroll */
        if (document.location.search.indexOf('container=calendar') !== -1) {
            document.getElementById('gadget').style.height = '200px';
            log('Calendar height fixing');
        }
        
        function refresh() {
            log('Issue refresh');
            var $time = $('#reload_now');
            var previous_time = $time.text();
            $time.removeClass('error').text('Ładowanie...');
            $('#gadget').load('/gadget #content', function(response, status, xhr){
                log('Refresh returned with status ' + status);
                if (status == "error") {
                    $time.addClass('error').text(previous_time);
                } else {
                    $time.removeClass('error');
                }
                resize();
            });
        }
        
        $('#reload_now').live('click', function() {
            log('Reload now clicked');
            refresh();
            return false;
        });

        /* reload gadget after timeout */
        var loop = function(){
            refresh();
            setTimeout(loop, TIMEOUT);
        }

        setTimeout(loop, TIMEOUT);
        resize();
    });
})(jQuery);

