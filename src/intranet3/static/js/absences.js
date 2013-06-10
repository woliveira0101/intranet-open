function generateTable(data) {
    console.log(data);
    // All necessary variables
    var today = new Date();
    var todayString = $.datepicker.formatDate('yy-mm-dd', today);
    var dayLetters = ['M', 'T', 'W', 'M', 'F', 'S', 'S'];
    var startDay = data.startDay.day;
    var dayOfWeek = data.startDay.dow;

    var $table = $('#example');
    $table.hide();
    // Table generator
    var $thead = $('#example thead');
    var $tbody = $('#example tbody');
    var singleRowStub = $('<tr />');
    var rows = [];
    // Header 1: month's name (July)
    var header1 = $('<tr />');
    // Header 2: month's days (1, 2, 3...)
    var header2 = $('<tr />');
    // Header 3: week days (M, T, W...)
    var header3 = $('<tr />');
    header1.append('<th rowspan="3">User</th>');
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
            var td = $('<td />').addClass(dayId);
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
    $thead.append(header1);
    $thead.append(header2);
    $thead.append(header3);
    _.each(data.users, function(u){
        var row = singleRowStub.clone();
        row.prepend('<td class="user">'+u.name+'</td>');
        if(u.id in data.absences) { // Absences
            _.each(data.absences[u.id], function(what, when){
                row.find('.'+when).addClass(what[0]).attr('title', what[1]);
            });
        }
        if(u.id in data.lates) { // Latenesses
            _.each(data.lates[u.id], function(why, when){
                row.find('.'+when).addClass('late').attr('title', why);
            });
        }
        rows.push(row);
    });
    $tbody.append(rows);
    $table.show();
}