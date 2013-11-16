var App = angular.module('intranet');


App.controller('absenceCtrl', function($scope, $http, $dialog, dialog) {
    $scope.errors = {};
    $scope.absence = {popup_type: "planowany"};

    $scope.close = function() {
        dialog.close();
    };

    $scope.add = function() {
        $scope.form_submitted = true;

        $http.post('/api/absence', {
            absence: $scope.absence
        }).success(function(data) {
            $scope.close();

            $dialog.dialog({
                resolve: {messages: function() {return data;}}
            }).open('modalConfirm.html', 'modalConfirmCtrl');
        }).error(function(data) {
            $scope.absenceForm.$setPristine();
            $scope.errors = {};

            angular.forEach(data, function(errors, field) {
                $scope.absenceForm[field].$setValidity('server', false);
                $scope.errors[field] = errors.join('<br/>');
            });

            $scope.form_submitted = false;
        });
    };

    $scope.updateDays = function() {
        if($scope.absence.popup_date_start) {
            $http.get('/api/absence_days', {
                params: {
                    date_start: $scope.absence.popup_date_start,
                    date_end: $scope.absence.popup_date_end,
                    type: $scope.absence.popup_type
                }
            }).success(function(data) {
                $scope.days = data.days;
                $scope.mandated = data.mandated;
                $scope.left = data.left;
            }).error(function(data) {
                $scope.errors['absence_days'] = '';
                angular.forEach(data, function(errors, field) {
                    $scope.errors['absence_days'] += field + ': ' + errors.join(', ');
                });
            });
        }
    };
});
