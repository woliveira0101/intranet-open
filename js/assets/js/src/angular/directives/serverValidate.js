var App = angular.module('intranet');


App.directive('serverValidate', function() {
    return {
        require: "^form",
        link: function ($scope, $el, attr, form) {
            $el.on('change', function() {
                $scope.$apply(function() {
                    var name = $el.attr('name');

                    form[name].$setValidity('server', true);
                    if($scope.$parent.errors) {
                        delete $scope.$parent.errors[name];
                    }
                    if($scope.errors) {
                        delete $scope.errors[name];
                    }
                });
            });
        }
    };
});
