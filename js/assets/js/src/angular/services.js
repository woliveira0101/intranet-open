angular.module('intranet')
    .service('date_of_birth', function(){
        return {

            create: function(START, END){

                var cls = function(){
                    var first = 0;
                    var second = 1;
                    var penult = END-START+3;
                    var last = END-START+4;

                    this.start = null;
                    this.end = null;
                    this.years = ['Date of birth'].concat(
                        ['Before ' + START],
                        _.range(START, END+1),
                        ['After '+ END],
                        ['Custom']
                    );
                    this.chosen = this.years[first];

                    this.set_range = function(start, end){
                        this.start = start;
                        this.end = end;
                    };

                    this.select_year = function(){
                        var chosen = this.years.indexOf(this.chosen);
                        switch (chosen){
                            case first:
                                this.set_range(null, null);
                                break;
                            case second:
                                this.set_range(START-50, START-1);
                                break;
                            case penult:
                                this.set_range(END+1, 2100);
                                break;
                            case last:
                                this.set_range(START, END);
                                break;
                            default:
                                var y = START + chosen - 2;
                                this.set_range(y, y);
                        }
                    };

                    this.is_custom = function() {
                        return this.years.indexOf(this.chosen)==last;
                    };

                    var count_years_occurrences = function(users){
                        var years = _.map(users, function(user){
                            if (user.date_of_birth)
                                return user.date_of_birth.substring(0,4);
                            else
                                return null;
                        });
                        years = _.compact(years);
                        var counts = {};
                        for(var i = 0; i < years.length; i++) {
                            var num = years[i];
                            counts[num] = counts[num] ? counts[num]+1 : 1;
                        }
                        return counts;
                    };

                    this.update_years = function(users){
                        var counts = count_years_occurrences(users);

                        // special cases for START > years > END
                        var before_start = 0;
                        var after_end = 0;
                        for (var i=1; i<100; i++){
                            before_start += counts[START-i] || 0;
                            after_end += counts[END+i] || 0;
                        }
                        if (before_start)
                            this.years[second] += ' (' + before_start + ')';
                        if (after_end)
                            this.years[penult] += ' (' + after_end + ')';

                        // the middle years
                        for (var i=second+1; i<penult; i++){
                            var n = counts[this.years[i]];
                            if (n)
                                this.years[i] += ' ('+ n + ')';
                        }
                    }
                };
                return new cls();
            }
        };
    }
);
