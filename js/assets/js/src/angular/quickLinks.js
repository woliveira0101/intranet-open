var App = angular.module('intranet');


App.controller('quickLinksCtrl', function($scope, $http, $location, $dialog) {
    $scope.lateness = function(mobile) {
        if(mobile) {
            $location.path('/mobile/lateness');
        } else {
            $dialog.dialog().open('lateness.html', 'latenessCtrl');
        }
    };

    $scope.absence = function() {
        $dialog.dialog().open('absence.html', 'absenceCtrl');
    };

    $scope.usersList = function() {
        $location.path('/mobile/user/list');
    };

    $scope.quickLinks = [
        {label: "Users list", func: $scope.usersList},
        {label: "Out of office form", func: $scope.lateness}
    ];
});
