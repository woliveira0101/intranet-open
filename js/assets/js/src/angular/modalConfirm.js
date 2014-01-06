var App = angular.module('intranet');


function capitalize(str) {
    var proper_str = str.replace('_', ' ');
    return proper_str[0].toUpperCase() + proper_str.slice(1);
}


App.controller('modalConfirmCtrl', function($scope, $http, $sce, dialog, messages) {
    $scope.close = function() {
        dialog.close();
    };

    var message = "";
    if(angular.isObject(messages)) {
        angular.forEach(messages, function(yes, msg) {
            message += capitalize(msg) + (yes ? "" : " not") + " added<br/>";
        });
    } else if(angular.isString(messages)) {
        message = angular.fromJson(messages);
    }
    $scope.message = $sce.trustAsHtml(message);
});
