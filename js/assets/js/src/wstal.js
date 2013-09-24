
var App = angular.module('intranet');

App.controller('wstalCtrl', function($scope, $http, $dialog) {
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
    };
    $scope.openModal = function(){
      var d = $dialog.dialog({
          resolve: {
            $callerScope: function() {return $scope}
          }
        });
      d.open('black_list.html', 'blackListCtrl');
    };
});

App.controller('blackListCtrl', function($scope, $http, $timeout, dialog, $callerScope) {
  $scope.lates = $callerScope.lates;
  $scope.absences = $callerScope.absences;
  $scope.data = _.extend($scope.lates, $scope.absences)
  console.log($scope.data);
  $scope.close = function(){
    dialog.close();
  };
});