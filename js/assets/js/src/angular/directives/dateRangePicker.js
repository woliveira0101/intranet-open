var App = angular.module('intranet');

App.directive('dateRangePicker', function() {
  return {
    require: 'ngModel',
    link: function(scope, el, attr, ngModel) {
      $(el).daterangepicker({
        format: 'MM/dd/yyyy'
      },
      function (start, end) {
        scope.$apply(function() {
          ngModel.$setViewValue({
            start: start,
            end: end
          });
        });
      });
    }
  };
});
