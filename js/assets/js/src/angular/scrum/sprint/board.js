var App = angular.module('intranet');

App.controller('sprintBoardCtrl', function($scope, $location) {
    $scope.filter_colors = filter_colors;

    $scope.filter = function(selected_color) {
        var url = window.location.origin + window.location.pathname +
            "?sprint_id=" + sprint_id;

        if (selected_color.color){
            url += "&color=" + selected_color.color.substr(1);
        }

        window.location = url;
    }
});
