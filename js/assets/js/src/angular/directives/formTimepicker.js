var App = angular.module('intranet');

App.directive('formTimepicker', function() {
    return {
        restrict: 'E',
        require: 'ngModel',
        scope: {
            name: "@",
            defaultTime: "@",
            ngModel: "="
        },
        transclude: true,
        replace: true,
        templateUrl: 'form/timepicker.html'
    };
});
