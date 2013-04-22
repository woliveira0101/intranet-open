(function($){

    /**
     * Add method to format string
     */
    String.prototype.format = function() {
        var pattern = /\{\d+\}/g;
        var args = arguments;
        return this.replace(pattern, function(capture) {
            return args[capture.match(/\d+/)];
        });
    };

    /**
     * Start Timer
     */
    var intervals_list = [],
        TIMEOUT = 3600;

    function clear_intervals_list(){
        var i,
            len = intervals_list.length;
        
        if(len > 0){
            for(i=0; i<len; i++){
                var id = intervals_list[i];
                clearInterval(id);
            }
        }
        intervals_list = [];
    }

    /**
     * Bind post for start/end timer
     * Create intervals for timers
     */
    function start_timers(){
        var total_sum_field = $('#time_entries tfoot td.sum-count');

        $('a#start-timer').each(function(i){
            var obj = $(this),
                id = obj.attr('title'),
                href = '/times/',
                timer_ts = obj.attr('date'),
                time_field = obj.parents('tr').find('td.time'),
                actual_time = time_field.text().split(':'),
                hours = parseInt(actual_time[0], 10),
                minutes = parseInt(actual_time[1], 10),
                status,
                intervalID;

            function update_time(){
                var seconds = (new Date() - timer_ts) / 1000; //seconds
                var min = (hours * 60) + minutes + (seconds / 60);
                
                var h = Math.floor(min / 60),
                    m = Math.floor(min % 60),
                    fm = m.toFixed();
                if (fm.length < 2) {
                    fm = "0" + fm;
                }
                time_field.text('{0}:{1}'.format(h.toFixed(), fm));
            }

            if($(this).hasClass('start')){
                status = 'start_timer';
            } else {
                status = 'stop_timer';
                timer_ts = new Date(parseInt(timer_ts));
                intervalID = setInterval(update_time, TIMEOUT);
                intervals_list.push(intervalID);
                obj.parents('tr').addClass('timer_on');
            }

            $(this).click(function(e){
                e.preventDefault();
                var post_link = href + status + '?timeentry_id=' + id;

                $.post(post_link, {}, function(data){
                    var text;
                    if(data.status === 'success'){
                        if(status === 'start_timer'){
                            text = 'Stop Timer';
                            obj.removeClass('start').addClass('stop');
                            obj.addClass('btn-primary')
                            obj.parents('tr').find('input.superkurazu').addClass('off');
                            intervalID = setInterval(update_time, TIMEOUT);
                            timer_ts = new Date();
                            status = 'stop_timer';
                            obj.parents('tr').addClass('timer_on');
                        } else {
                            text = 'Start Timer';
                            time_field.text(data.time);
                            total_sum_field.text(data.total_sum);
                            obj.removeClass('stop').addClass('start');
                            obj.removeClass('btn-primary');
                            clearInterval(intervalID);
                            status = 'start_timer';
                            obj.parents('tr').removeClass('timer_on');
                        }
                        obj.text(text);
                    }
                }, 'json');
            });
        });
    }

    /**
     * Add time entry using ajax
     */
    function ajax_add_time_entry(e){
        var form = $(this).parents('form');
        var time_field = $(form).find('.time_entry_time');
        var self = this;
        var url = form.attr('action').split('?');

        url[url.length-2] = '/times/ajax_add';
        url = url.join('?');

        if(typeof form !== 'undefined'){
            e.preventDefault();
            $.post(url, form.serialize(), function(data){
                if(data.status === 'success'){
                    $(self).parents('tbody').find('tr.error, tr.success').remove();
                    $(self).parents('tbody').prepend('<tr class="success"><td colspan="5">Time entry added</tr>');
                    $('#time_entries').replaceWith(data.html);
                    time_field.val('');
                    clear_intervals_list(); // clear intervals
                    start_timers(); // start new intervals
                } else {
                    $(self).parents('tbody').find('tr.error, tr.success').remove();
                    $(self).parents('tbody').prepend('<tr class="error"><td colspan="5">'+ data.errors +'</tr>');
                }
            }, 'json');
        }
    }

    /* DOM ready */
    $(function(){
        $.tablesorter.addParser({
            // set a unique id
            id: 'priority',
            is: function(s) {
                return false;
            },
            format: function(s, table, node) {
                var $node = $(node);
                var sort_attr = $node.attr('data-sort');
                return sort_attr;
            },
            // set type, either numeric or text
            type: 'numeric'
        });
        $.tablesorter.addParser({
            // set a unique id
            id: 'status',
            is: function(s) {
                return false;
            },
            //'NEW', 'ASSIGNED', 'REOPENED', 'UNCONFIRMED', 'CONFIRMED', 'WAITING', 'RESOLVED', 'VERIFIED', 'CLOSED'
            format: function(s) {
                var result = s.toLowerCase() // severity
                    .replace(/new/, 1)
                    .replace(/assigned/, 2)
                    .replace(/reopened/, 3)
                    .replace(/confirmed/, 4)
                    .replace(/waiting/, 5)
                    .replace(/resolved/, 6)
                    .replace(/verified/, 7)
                    .replace(/closed/, 8)
                    .replace(/resolved/, 9);
                return result
            },
            // set type, either numeric or text
            type: 'numeric'
        });
        $("table.sort-table").tablesorter();
        $("table.sort-sprint-table").tablesorter({
            headers: {
                3: {
                    sorter:'priority'
                },
                8: {
                    sorter:'status'
                }
            }
        });

        $('a.external').click(function(){
            window.open(this.href);
            return false;
        });
       
        $('a.fancybox').fancybox({
            'width'             : '100%',
            'height'            : '100%',
            'autoScale'         : false,
            'transitionIn'      : 'none',
            'transitionOut'     : 'none',
            'type'              : 'iframe'
        });

        start_timers(); //timers
        //$('input#add_time_entry').live('click', ajax_add_time_entry); //ajax add entry

        /**
         * Defaults settings for all datepickers
         */
        $.datepicker.setDefaults({
            showOn: "button",
            buttonImage: "/static/img/calendar.gif",
            buttonImageOnly: true,
            changeMonth: true,
            changeYear: true,
            dateFormat: 'mm/dd/yy'
        });

        var usertooltip = (function(){
            var users = {}, isShow = false, x = 0, y = 0, xhr = null;
            var get = function(uid,fn){
                if(xhr){
                    xhr.abort();
                }
                if(uid in users){
                    fn(users[uid]);
                }else{
                    xhr = $.get('/user/tooltip?user_id='+uid,function(html){
                        xhr = null;
                        users[uid] = html;
                        fn(html);
                    });
                }
            };
            var pos = function(){
                if(isShow){
                   $dom.css({
                       left:x,
                       top:y
                   });  
                }
            };
            var show = function(uid){
                isShow = true;
                pos();
                $dom.html('Loading...').show();
                get(uid,function(html){
                    $dom.html(html);
                });    
            };
            var hide = function(){
                isShow = false;
                $dom.hide();
            }

            var $dom = $('<div>',{
                id:'users-tootip'
            });
            $('body').append($dom);
            var _t;
            return {
                pos:function(_x,_y){
                    x = _x;
                    y = _y;
                    pos();
                },
                show:function(uid){
                    clearTimeout(_t);
                    _t = setTimeout(function(){
                        show(uid);
                    },300);
                    hide();
                },
                hide:function(){
                    clearTimeout(_t);
                    _t = setTimeout(function(){
                        hide();
                    },10);  
                }
            };
        })();

        $('[class^="x-user-tooltip-"]').each(function(){
            $item = $(this);
            var uid = $item.prop('class').match(/x-user-tooltip-(\d+)/)[1];
            if(uid){
                $item.mouseenter(function(){
                    usertooltip.show(uid);
                }).mouseleave(function(){
                    usertooltip.hide();
                });
            }
        });
        $(document).mousemove(function(e){
            usertooltip.pos(e.pageX,e.pageY);
        });

        $('a.a_popup').each(function(i, el) {
            var $el;

            $el = $(el);

            $el.fancybox({
                'autoDimensions' : true,
                'scrolling' : 'no',
                'height' : '100%',
                'type' : 'ajax'
            });
        });

        $(".ajax-loader").ajaxStart(function(){
            $(this).show();
        }).ajaxStop(function(){
            $(this).hide();
        });

        $('.alt-submit').click(function(){
            /*
                Way to add alternative action and method to form and submit it.
                  <form action="/abc" method="POST" data-alt_action="/def" data-alt_method="GET">
                  <input type="submit" value="Primary submit"/>
                  <a class="alt-submit" href="#">Alternative submit</a>
                  </form>
             */
            var $form = $(this).closest('form');
            var alt_action = $form.attr('data-alt_action');
            var alt_method = $form.attr('data-alt_method');
            var old_action = $form.attr('action');
            var old_method = $form.attr('method');
            $form.attr('action', alt_action);
            $form.attr('method', alt_method);
            $form.submit();
            $form.attr('action', old_action);
            $form.attr('method', old_method);
            return false;
        });

        $('.datepicker-GET').datepicker({
            dateFormat: 'dd-mm-yy',
            showOn: 'focus'
        });

        $('.datepicker').datepicker({
            dateFormat: 'dd/mm/yy',
            showOn: 'focus'
        });

        $('.bootstrap-tooltip').tooltip();

        $('.daterange').daterangepicker(
            {
                ranges: {
                    'Today': ['today', 'today'],
                    'Yesterday': ['yesterday', 'yesterday'],
                    'This Week': IL.weekrange(),
                    'Last Week': IL.weekrange(-1),
                    'This Month': [Date.today().moveToFirstDayOfMonth(), Date.today().moveToLastDayOfMonth()],
                    'Last Month': [Date.today().moveToFirstDayOfMonth().add({ months: -1 }), Date.today().moveToFirstDayOfMonth().add({ days: -1 })]
                },
                opens: 'right',
                format: 'dd-MM-yyyy',
                separator: ' - ',
                startDate: Date.today().moveToFirstDayOfMonth(),
                endDate: Date.today().moveToLastDayOfMonth(),
                locale: {
                    applyLabel: 'Submit',
                    fromLabel: 'From',
                    toLabel: 'To',
                    customRangeLabel: 'Custom Range',
                    daysOfWeek: ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr','Sa'],
                    monthNames: ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'],
                    firstDay: 1
                },
                showWeekNumbers: true,
                buttonClasses: ['btn-danger']
            }
        );


        /*
        We need those selectors in 2 places so they landed here.
         */
        var $ticket_grouping = $('#ticket-grouping');
        if($ticket_grouping.length){
            var $group_by_client = $ticket_grouping.find('#group_by_client');
            var $group_by_project = $ticket_grouping.find('#group_by_project');
            var $group_by_bugs = $ticket_grouping.find('#group_by_bugs');

            $group_by_bugs.change(function(){
                if($(this).is(':checked')){
                    $group_by_client.prop('checked', true);
                    $group_by_project.prop('checked', true);
                }
            });
            $group_by_project.change(function(){
                if($(this).is(':checked')){
                    $group_by_client.prop('checked', true);
                } else {
                    $group_by_bugs.prop('checked', false);
                }
            });
            $group_by_client.change(function(){
                if(!$(this).is(':checked')){
                    $group_by_project.prop('checked', false);
                    $group_by_bugs.prop('checked', false);
                }
            });
        }

    });
})(jQuery);

// IH - intranet helpers
(function(IH, $, _,  undefined ){
    IH.inloop = function(delay, f){
        (function loop_f() {
            setTimeout(function(){
                f();
                loop_f();
            }, delay)
        })();
    }
}( window.IH = window.IH || {}, jQuery, _ ));

// IL - intranet library
(function(IL, $, _, Date,  undefined ){

    IL.weekrange = function(date, offset){
        if(date === undefined ){
            date = Date.today();
            offset = 0;
        } else if ( typeof(date) === 'string' || typeof(date) === 'number'){
            offset = date;
            date = Date.today()
        } else if (offset === undefined){
            offset = 0;
        }
        offset = parseInt(offset)

        var first = new Date(date.getTime()), last = new Date(date.getTime());

        if(date.getDay() !== 1){
            first.moveToDayOfWeek(1, -1);
            last.moveToDayOfWeek(1, -1);
        }

        first.add({ days: 7*offset });
        last.add({ days: 7*offset });
        last.add({ days: 6});

        return [first, last]
    }

}( window.IL = window.IL || {}, jQuery, _, Date ));
