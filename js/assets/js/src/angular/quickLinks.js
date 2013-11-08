var App = angular.module('intranet');


App.controller('quickLinksCtrl', function($scope, $http, $dialog) {
    $scope.lateness = function() {
        $dialog.dialog().open('lateness.html', 'latenessCtrl');
    };

    $scope.absence = function() {
        $dialog.dialog().open('absence.html', 'absenceCtrl');
    };
});
