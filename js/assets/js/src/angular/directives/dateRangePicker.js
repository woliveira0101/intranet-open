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
      $(el).daterangepicker(
        {
          format: format
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
