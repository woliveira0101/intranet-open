var App = angular.module('intranet');

App.directive('jqdatepicker', function() {
  return {
    require: 'ngModel',
    link: function(scope, el, attr, ngModel) {
      $(el).datepicker({
        dateFormat: 'dd/mm/yy',
        showOn: 'focus',
        onSelect: function(dateText) {
          scope.$apply(function() {
            ngModel.$setViewValue(dateText);
          });
        }
      });
    }
  };
});
