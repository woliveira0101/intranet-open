var App = angular.module('intranet');

App.directive('jqdatepicker', function() {
  return {
    require: 'ngModel',
    link: function(scope, el, attr, ngModel) {
      el.datepicker({
        dateFormat: 'dd/mm/yy',
        showOn: 'focus',
        onSelect: function(dateText) {
          scope.$apply(function() {
            ngModel.$setViewValue(dateText);
          });
          el.trigger('change');
        }
      });
      if(attr.defaultDate) {
          if(attr.defaultDate === 'today') {
              var date = $.datepicker.formatDate('dd/mm/yy', new Date());
          } else {
              var date = attr.defaultDate;
          }
          el.val(date);
          ngModel.$setViewValue(date);
      }
    }
  };
});
