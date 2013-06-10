function generateTable(data) {
    // All necessary variables
    var today = new Date();
    var todayString = $.datepicker.formatDate('yy-mm-dd', today);
    var dayLetters = ['M', 'T', 'W', 'M', 'F', 'S', 'S'];
    var startDay = data.startDay.day;
    var dayOfWeek = data.startDay.dow;

    $tables = $('.absences table');
    $tables.hide();
    // Selectors
    var $days = $('#days thead');
    var $users = $('#users tbody');
    var $data = $('#data tbody');
    var singleRowStub = $('<tr />');
    var rows = [];

    // Generate all headers!
    // Header 1: month's name (July)
    var header1 = $('<tr />');
    // Header 2: month's days (1, 2, 3...)
    var header2 = $('<tr />');
    // Header 3: week days (M, T, W...)
    var header3 = $('<tr />');
    var first = true;
    _.each(data.months, function(m){
        var firstMonth = (data.months.indexOf(m) == 0);
        // Headers
        var colspan = firstMonth ? m[1]-startDay+1 : m[1];
        var headTd = $('<th/>').text(m[0]).attr('colspan', colspan).addClass('month');
        header1.append(headTd);
        var iTemp = firstMonth ? startDay : 1;
        for(var i=iTemp; i<=m[1]; i++) {
            var dayId = data.year + '-' + (m[2]<10 ? '0' : '') + m[2] + '-' + (i<10 ? '0' : '') + i
            var head2Td = $('<th class="day">'+i+'</th>');
            var head3Td = $('<th class="day">'+dayLetters[(dayOfWeek%7)]+'</th>');
            var td;
            if(first) {
                td = $('<td class="'+dayId+'">&nbsp;</td>');
                first = false;
            } else {
                td = $('<td />');
            }
            td.addClass(dayId);
            if(i == m[1]) { // End of the month
                head2Td.addClass('monthend');
                head3Td.addClass('monthend');
                td.addClass('monthend');
            }
            if(dayOfWeek%7 >= 5 || data.holidays.indexOf(dayId) != -1) { // Saturday, Sunday or Holiday
                head2Td.addClass('holiday');
                head3Td.addClass('holiday');
                td.addClass('holiday');
            }
            if(dayId === todayString) { // Today
                head2Td.addClass('today');
                head3Td.addClass('today');
                td.addClass('today');
            }
            header2.append(head2Td);
            header3.append(head3Td);
            singleRowStub.append(td);
            dayOfWeek++;
        }
    });

    // Generate all users!
    users = '';
    _.each(data.users, function(u){
        var row = singleRowStub.clone();
        users += '<tr><td class="user">'+u.name+'</td></tr>';
        if(u.id in data.absences) { // Absences
            _.each(data.absences[u.id], function(attr, start){
                // attr: [length, type, description]
                var $td = row.find('.'+start);
                $td.addClass(attr[1]).attr({
                    colspan: attr[0],
                    title: attr[2]
                });
                $td.nextAll(':lt('+(attr[0]-1)+')').remove();
            });
        }
        if(u.id in data.lates) { // Latenesses
            _.each(data.lates[u.id], function(why, when){
                row.find('.'+when).addClass('late').attr('title', why);
            });
        }
        rows.push(row);
    });

    // Append!
    $days.append(header1);
    $days.append(header2);
    $days.append(header3);
    $users.append(users);
    $data.append(rows);
    $tables.show();
}

$(function(){
    var width = $(window).innerWidth(),
        height = $(window).innerHeight();
    $('#data, #days').parent().width(width-500);
    $('#data, #users').parent().height(height-230);
    var $p = $('#data').parent();
    $p.on('scroll', function(e){
        $('#days').parent().scrollLeft($p.scrollLeft());
        $('#users').parent().scrollTop($p.scrollTop());
    });
});
