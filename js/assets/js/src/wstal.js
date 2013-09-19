
angular.module('intranet').controller('wstalCtrl', function($scope, $http) {
    $scope.show_box = false;
    $scope.from = 'From';
    $scope.to = 'To';
    $http.get('/api/presence').success(function(data){
        $scope.lates = _.filter(data.lates, function(user){
            return user.id !== G.user.id;
        });
        $scope.absences = data.absences;
        if (data.lates.length == 0) ($scope.from = '', $scope.to = '');
    });
    $scope.show = function(){
        if ($scope.lates.length != 0 || $scope.absences.length != 0) ($scope.show_box = ! $scope.show_box);
    };
    $scope.set_time = function(time_str){
        return Date.parse(time_str)
    }
});