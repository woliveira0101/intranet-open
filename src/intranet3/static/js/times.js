(function(){
    (function(){
        // when user choose Edition1 project, we show him checbox button to add times to harvest application.
        var $project_id = $('#project_id');
        var check_checkbox = function(){
            var $add_to_harvest = $('#add-to-harvest');
            var id = $project_id.val();
            var project_name = $project_id.find('option[value="'+id+'"]').text();
            if(project_name.indexOf('Edition1') !== -1){
                $add_to_harvest.show()
            } else {
                $add_to_harvest.hide()
            }
        };
        check_checkbox();
        $project_id.change(function(){
            check_checkbox();
        });
    })();
    (function(){
        // add select tag Ticket type for predefined ticket ids like M0, M1, M2 etc.
        var $ticket_desc = $('#description');
        var $ticket_type = $('#ticket-type');
        var $ticket_id = $('#ticket_id');
        var add_ticket_type_options = function(){
            _.each(types, function(type){
                $ticket_type.append($('<option></option>', {value: type.value, text:type.desc}))
            })
        };

        (function(){
            add_ticket_type_options();
            var value = $ticket_id.val();
            if(_.any(types, function(v){ return v.value===value})){
                $ticket_type.val(value);
                $ticket_id.prop('readonly', true);
            } else {
                $ticket_id.prop('readonly', false);
            }
        })();

        $ticket_type.change(function(){
            var value = $ticket_type.val();
            var text = $('#ticket-type :selected').text();
            if(value !== 'M0'){
                $ticket_id.val(value);
                $ticket_id.prop('readonly', true);
                $ticket_desc.val(text);
            } else {
                $ticket_id.val('');
                $ticket_id.prop('readonly', false);
                $ticket_desc.val('');
            }
        })
    })();
})();