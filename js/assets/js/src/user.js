var App = angular.module('intranet', ['ngDragDrop', 'ui.bootstrap']);

App.controller('usersCtrl', function($scope, $http, $dialog) {
    $scope.users = [];
    $scope.filtered_out_users = [];
    $scope.search = {
      name: '',
      start_work: ''
    };

    $scope.employees = function(){
        return _.filter($scope.users, function(user){
            return user.name.length > 15;
        });
    };


    $http.get('/api/users?full=1').success(function(data){
       $scope.users = data;

    });

    $scope.filter = function(){
        var user;
        if($scope.filtered_out_users.length > 0){
            user = $scope.filtered_out_users.splice(0, 1)[0];
            $scope.users.push(user);
        } else {
            user = $scope.users.splice(0, 1)[0];
            $scope.filtered_out_users.push(user);
        }
    };

});