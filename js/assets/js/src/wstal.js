
var App = angular.module('intranet');

App.controller('wstalCtrl', function($scope, $http, $dialog) {
    $scope.show_box = false;

    $http.get('/api/users').success(function(data){
        $scope.users = data;
    });

    $http.get('/api/presence').success(function(data){
        $scope.lates = data.lates;
        $scope.absences = data.absences;
        $scope.blacklist = data.blacklist;
    });


    $scope.get_lates = function(){
        return _.filter($scope.lates, function(user){
           return $scope.blacklist.indexOf(user.id) < 0;
        });
    };

    $scope.get_absences = function(){
        return _.filter($scope.absences, function(user){
           return $scope.blacklist.indexOf(user.id) < 0;
        });
    };


    $scope.show = function(){
        $scope.show_box = !$scope.show_box;
    };


    $scope.set_time = function(time_str){
        return Date.parse(time_str)
    };

    $scope.openModal = function(){
        var d = $dialog.dialog({
            resolve: {
                $callerScope: function() {return $scope}
            }
        });
        d.open('blacklist.html', 'blackListCtrl');
    };

    $scope.delete = function(user_id){
        $scope.blacklist.push(user_id);
    };

});

App.controller('blackListCtrl', function($scope, $http, $timeout, dialog, $callerScope) {
    $scope.users = $callerScope.users;
    $scope.blacklist = $callerScope.blacklist;

    $scope.close = function(){
        dialog.close();
    };

    $scope.edit = function(){
        $callerScope.blacklist = $scope.blacklist;
        dialog.close();
        $http.post('/api/blacklist', {
            blacklist:$scope.blacklist
        })
    };
});