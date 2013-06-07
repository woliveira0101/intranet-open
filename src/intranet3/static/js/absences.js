function generateTable(data) {
    console.log(data);
    var today = new Date();
    var dayLetters = ['M', 'T', 'W', 'M', 'F', 'S', 'S'];
    var startDay = data.startDay.day;
    var dayOfWeek = data.startDay.dow;
    var $table = $('#example');
    $table.hide();
    // Table generator
    var $thead = $('#example thead');
    var singleRowStub = $('<tr />');
    var rows = [];
    var header1 = $('<tr />'), header2 = $('<tr />'), header3 = $('<tr />');
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
            var head1Td = $('<th class="day">'+i+'</th>');
            var head2Td = $('<th class="day">'+dayLetters[(dayOfWeek%7)]+'</th>');
            var td = $('<td />').addClass(dayId);
            if(i == m[1]) {
                head1Td.addClass('monthend');
                head2Td.addClass('monthend');
                td.addClass('monthend');
            }
            if(dayOfWeek%7 >= 5 || data.holidays.indexOf(dayId) != -1) {
                head1Td.addClass('holiday');
                head2Td.addClass('holiday');
                td.addClass('holiday');
            }
            header2.append(head1Td);
            header3.append(head2Td);
            singleRowStub.append(td);
            dayOfWeek++;
        }
    });
    $thead.append(header1);
    $thead.append(header2);
    $thead.append(header3);
    _.each(data.users, function(u){
        var row = singleRowStub.clone();
        row.prepend('<td class="user">'+u+'</td>');
        rows.push(row);
    });
    $table.append(rows);
    $table.show();
}