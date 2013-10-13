var App = angular.module('intranet');

App.directive('dateRangePicker', function($compile) {
  return {
    require: 'ngModel',
    link: function(scope, el, attr, ngModel) {
      var format = 'dd-MM-yyyy';
      ngModel.$formatters.push(function(value){
        if(value && value.start && value.end){
          var start = value.start.toString(format);
          var end = value.end.toString(format);
          return start + ' - ' + end;
        }
        return '';
      });
      var thisYearStart = new Date(new Date().getFullYear(), 0, 1);
      var thisYearEnd = new Date(new Date().getFullYear(), 11, 31);
      var lastYearStart = new Date(new Date().getFullYear()-1, 0, 1);
      var lastYearEnd = new Date(new Date().getFullYear()-1, 11, 31);
      $(el).daterangepicker(
        {
          ranges: {
            'This Month': [Date.today().moveToFirstDayOfMonth(), Date.today().moveToLastDayOfMonth()],
            'Last Month': [Date.today().moveToFirstDayOfMonth().add({ months: -1 }), Date.today().moveToFirstDayOfMonth().add({ days: -1 })],
            'This Year': [thisYearStart, thisYearEnd],
            'Last Year': [lastYearStart, lastYearEnd]
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
        },
        function (start, end) {
          scope.$apply(function() {
            ngModel.$setViewValue({
              start: start,
              end: end
            });
          });
        }
      );
    }
  };
});
