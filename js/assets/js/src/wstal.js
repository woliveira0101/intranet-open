
angular.module('intranet').controller('wstalCtrl', function($scope, $http) {
    $scope.show_box = false;
    $http.get('/api/presence').success(function(data){
        $scope.lates = _.filter(data.lates, function(user){
            return user.id !== G.user.id;
        });
        $scope.absences = data.absences;
    });
    $scope.show = function(){
        $scope.show_box = ! $scope.show_box;
    };
    $scope.set_time = function(time_str){
        return Date.parse(time_str)
    }
});