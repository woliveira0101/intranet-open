var App = angular.module('intranet');


App.controller('quickLinksCtrl', function($scope, $http, $dialog, $timeout) {
    $scope.lateness = function() {
        var d = $dialog.dialog({
            resolve: {
                $callerScope: function() {return $scope}
            }
        });

        d.open('lateness.html', 'latenessCtrl');
    };
});
