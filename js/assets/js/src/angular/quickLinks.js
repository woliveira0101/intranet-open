var App = angular.module('intranet');


App.controller('quickLinksCtrl', function($scope, $http, $dialog) {
    $scope.lateness = function() {
        var d = $dialog.dialog({
            resolve: {
                $callerScope: function() {return $scope}
            }
        });

        d.open('lateness.html', 'latenessCtrl');
    };

    $scope.absence = function() {
        $dialog.dialog().open('absence.html', 'absenceCtrl');
    };
});
