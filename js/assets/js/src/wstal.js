
var App = angular.module('intranet');

App.controller('wstalCtrl', function($scope, $http, $dialog) {
    $scope.show_box = false;
    $scope.from = 'From';
    $scope.to = 'To';
    $http.get('/api/users').success(function(data){
        $scope.users = data;
//        ODKOMENTOWAĆ JEŚLI W USERACH DO SUBSKRYPCJI MA NIE
//                  WYŚWIETLAĆ SIĘ AKTUALNY USER
//        $scope.users = _.filter(data, function(user){
//            return user.id !== G.user.id;
//        });
    });
    $http.get('/api/presence').success(function(data){
        $scope.lates_wstal = data.lates;
        $scope.absences_wstal = data.absences;
        $scope.blacklist = data.blacklist;
//        ODKOMENTOWAĆ JEŚLI W USERACH DO SUBSKRYPCJI MA NIE
//                  WYŚWIETLAĆ SIĘ AKTUALNY USER
//        $scope.lates = _.filter(data.lates, function(user){
//            return user.id !== G.user.id;
//        });
        $scope.lates = _.filter($scope.lates_wstal, function(late){
            return typeof(_.find($scope.blacklist, function(sublate){
                return sublate == late.id; })) == 'undefined';
        });
        $scope.absences = _.filter($scope.absences_wstal, function(absence){
            return typeof(_.find($scope.blacklist, function(subabsence){
                return subabsence == absence.id; })) == 'undefined';
        });
        $scope.blacklist = data.blacklist;
        if (data.lates.length == 0) ($scope.from = '', $scope.to = '');
    });
    $scope.show = function(){
        if ($scope.lates.length != 0 || $scope.absences.length != 0)
            ($scope.show_box = ! $scope.show_box);
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
    $scope.close = function(){
        dialog.close();
    };
    $scope.edit = function(){
        $http.post('/api/blacklist', {
            blacklist:$scope.blacklist,
            lates:$callerScope.lates_wstal, absences:$callerScope.absences_wstal
        }).success(function(data){
            $callerScope.blacklist = data.blacklist;
            $callerScope.lates = data.lates;
            $callerScope.absences = data.absences;
            if (data.lates.length == 0 || data.absences.length == 0)
                $callerScope.show_box = false;
            dialog.close();
        });
    };
});