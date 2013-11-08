var App = angular.module('intranet');


function capitalize(str) {
    var proper_str = str.replace('_', ' ');
    return proper_str[0].toUpperCase() + proper_str.slice(1);
}


App.controller('modalConfirmCtrl', function($scope, $http, $dialog, dialog, messages) {
    $scope.close = function() {
        dialog.close();
    };

    if(angular.isObject(messages)) {
        $scope.message = "";
        angular.forEach(messages, function(yes, message) {
            $scope.message += capitalize(message) + (yes ? "" : " not") + " added<br/>";
        });
    } else if(angular.isString(messages)) {
        $scope.message = angular.fromJson(messages);
    }
});
