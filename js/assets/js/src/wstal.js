
var App = angular.module('intranet');

App.controller('wstalCtrl', function($scope, $http, $dialog) {
    $scope.show_box = false;
    $scope.from = 'From';
    $scope.to = 'To';
    $http.get('/api/users').success(function(data){
        $scope.users = _.filter(data, function(user){
            return user.id !== G.user.id;
        });
    });
    $http.get('/api/blacklist').success(function(data){
        $scope.blacklist = data;
    });
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
    };
    $scope.openModal = function(){
      var d = $dialog.dialog({
          resolve: {
            $callerScope: function() {return $scope}
          }
        });
      d.open('blacklist.html', 'blackListCtrl');
    };
});

App.controller('blackListCtrl', function($scope, $http, $timeout, dialog, $callerScope) {
    $scope.users = $callerScope.users;
    $scope.blacklist = $callerScope.blacklist;
    $http.get('/api/users').success(function(data){
    $scope.users = _.filter(data, function(user){
            return user.id !== G.user.id;
    });
    });
    $scope.close = function(){
    dialog.close();
    };
    $scope.edit = function(){
      $http.post('/api/blacklist', {
          blacklist:$scope.blacklist,
          lates:$callerScope.lates, absences:$callerScope.absences
      }).success(function(data){
          $callerScope.blacklist = data.blacklist;
          $callerScope.lates = data.lates;
          $callerScope.absences = data.absences;
          dialog.close();
      });
    };
});