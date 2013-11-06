var App = angular.module('intranet');

App.directive('formTimepicker', function() {
    return {
        restrict: 'E',
        require: 'ngModel',
        scope: {
            ngModel: "="
        },
        transclude: true,
        replace: true,
        templateUrl: 'form/timepicker.html',
        compile: function($el, attr) {
            var input = $el.find('input');

            input.attr('name', attr.name);
            input.attr('default-time', attr.defaultTime);
        }
    };
});
