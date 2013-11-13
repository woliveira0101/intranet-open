var App = angular.module('intranet');


App.controller('latenessCtrl', function($scope, $http, $location, $dialog, dialog) {
    $scope.errors = {};

    $scope.modal = !!dialog;

    $scope.close = function() {
        dialog.close();
    };

    $scope.add = function() {
        $scope.form_submitted = true;

        $http.post('/api/lateness', {
            lateness: $scope.lateness
        }).success(function(data) {
            if(!$scope.modal) {
                $location.path('/mobile/confirm').search(data);
            } else {
                $scope.close();

                $dialog.dialog({
                    resolve: {messages: function() {return data;}}
                }).open('modalConfirm.html', 'modalConfirmCtrl');
            }
        }).error(function(data) {
            $scope.latenessForm.$setPristine();
            $scope.errors = {};

            angular.forEach(data, function(errors, field) {
                $scope.latenessForm[field].$setValidity('server', false);
                $scope.errors[field] = errors.join('<br/>');
            });

            $scope.form_submitted = false;
        });
    };
});
