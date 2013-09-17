
angular.module('intranet').controller('wstalCtrl', function($scope, $http) {
    $scope.show_box = false;
    $http.get('/api/presence').success(function(data){
        console.log(data);
        $scope.late = data.late;
        $scope.user_id = data.user_id;
    });
    $scope.show = function(){
    $scope.show_box = ! $scope.show_box;
    }
    $scope.set_current_user = function(id){
        if (id == $scope.user_id) return "current_user";
    }
    $scope.set_time = function(str_time){
        return Date.parse(str_time);
    }
});
