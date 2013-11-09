var App = angular.module('intranet');


App.controller('latenessCtrl', function($scope, $http, $dialog, dialog) {
    $scope.errors = {};

    $scope.close = function() {
        dialog.close();
    };

    $scope.add = function() {
        $scope.form_submitted = true;

        $http.post('/api/lateness', {
            lateness: $scope.lateness
        }).success(function(data) {
            $scope.close();

            $dialog.dialog({
                resolve: {messages: function() {return data;}}
            }).open('modalConfirm.html', 'modalConfirmCtrl');
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
