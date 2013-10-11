var App = angular.module('intranet');

function updateLists($scope) {
    $scope.whitelist = _.filter($scope.users, function(user){
       return $scope.blacklistIds.indexOf(user.id) < 0;
    });
    $scope.blacklist = _.filter($scope.users, function(user){
       return $scope.blacklistIds.indexOf(user.id) >= 0;
    });
}

function parseLocalStorage($scope) {
    $scope.show_box = JSON.parse(localStorage['isLatesPreviewOpened'] || false);

    firstFetchToday = true;
    lastVisitDate = localStorage['lastVisitDate'];
    if (lastVisitDate != undefined) {
        if ((new Date(lastVisitDate)).isToday()) {
            firstFetchToday = false;
        }
    }

    if (firstFetchToday) {
        $scope.newLatesQuantity = 0;
        $scope.knownLatesIds = {};
        $scope.knownAbsencesIds = {};
    } else {
        $scope.knownLatesIds = JSON.parse(localStorage['knownLatesIds']);
        $scope.knownAbsencesIds = JSON.parse(localStorage['knownAbsencesIds']);
    }
}

function saveToLocalStorage($scope) {
    localStorage['knownLatesIds'] = JSON.stringify($scope.knownLatesIds);
    localStorage['knownAbsencesIds'] = JSON.stringify($scope.knownAbsencesIds);
    localStorage['lastVisitDate'] = new Date();
    localStorage['isLatesPreviewOpened'] = $scope.show_box;
}

function updateKnownIds($scope) {
    $scope.knownLatesIds = _.map($scope.lates, function(late) {
        return late.late_id;
    });
    $scope.knownAbsencesIds = _.map($scope.absences, function(absence) {
        return absence.absence_id;
    });
}

function findNewIds($scope, newData) {
    latesIds = _.map(newData.lates, function(late) {
        return late.late_id;
    });
    absencesIds = _.map(newData.absences, function(absence) {
        return absence.absence_id;
    });

    $scope.newLatesIds = _.difference(latesIds, $scope.knownLatesIds);
    $scope.newAbsencesIds = _.difference(absencesIds, $scope.knownAbsencesIds);
}

App.controller('wstalCtrl', function($scope, $http, $dialog, $timeout) {
    $("#dialogRemovalConfirmation").dialog({
      autoOpen: false,
      resizable: false,
      modal: true,
      closeText: "x",
      buttons: {
        "Add to black list": function() {
            $scope.delete($scope.blacklistProposal.id);
            $scope.$apply();
            $(this).dialog("close");
            $http.post('/api/blacklist', {
              blacklist: $scope.blacklistIds
            })
        },
        Cancel: function() {
            $(this).dialog("close");
        }
      },
      open: function(event, ui) {
        $('.ui-dialog-titlebar-close', ui.dialog).text('x');
        $('#proposalName').text(($scope.blacklistProposal.name));
      }
    });

    $http.get('/api/users').success(function(data){
        $scope.users = data.users;
    });

    $http.get('/api/presence').success(function(data){
        $scope.lates = data.lates;
        $scope.absences = data.absences;

        $scope.newLatesIds = [];
        $scope.newAbsencesIds = [];

        $scope.blacklistIds = data.blacklist;

        (function tick() {
            $http.get('/api/presence').success(function(data){
                parseLocalStorage($scope);

                if (firstFetchToday) {
                    updateKnownIds($scope);
                } else {
                    findNewIds($scope, data);
                }

                $scope.lates = data.lates;
                $scope.absences = data.absences;

                if (!$scope.show_box) {
                    $scope.newLatesQuantity = $scope.newLatesIds.length
                                                + $scope.newAbsencesIds.length;
                }
                saveToLocalStorage($scope);

                firstFetchToday = false;
                $timeout(tick, 60000);
                $('.tooltip').remove();
            });
        })();
    });


    $scope.get_lates = function(){
        return _.filter($scope.lates, function(user){
           return $scope.blacklistIds.indexOf(user.id) < 0 &&
                    !user.work_from_home;
        });
    };

    $scope.get_work_from_home = function(){
        return _.filter($scope.lates, function(user){
           return $scope.blacklistIds.indexOf(user.id) < 0 &&
                    user.work_from_home;
        });
    };

    $scope.get_absences = function(){
        return _.filter($scope.absences, function(user){
           return $scope.blacklistIds.indexOf(user.id) < 0;
        });
    };


    $scope.show = function(){
        if ($scope.show_box) {
            updateKnownIds($scope);

            $scope.newLatesIds = [];
            $scope.newAbsencesIds = [];
        }

        $scope.show_box = !$scope.show_box;
        $scope.newLatesQuantity = 0;
        saveToLocalStorage($scope);
    };


    $scope.set_time = function(time_str){
        return Date.parse(time_str)
    };

    $scope.openModal = function(){
        updateLists($scope);

        var d = $dialog.dialog({
            resolve: {
                $callerScope: function() {return $scope}
            }
        });
        d.open('blacklist.html', 'blackListCtrl');
    };

    $scope.openRemovalConfirmation = function(user) {
        $scope.blacklistProposal = user;
        $("#dialogRemovalConfirmation").dialog("open")
    }

    $scope.delete = function(user_id){
        $scope.blacklistIds.push(user_id);
    };

});

App.controller('blackListCtrl', function($scope, $http, $timeout,
                                        dialog, $callerScope) {
    $scope.users = $callerScope.users;
    $scope.blacklistIds = $callerScope.blacklistIds;
    $scope.blacklist = $callerScope.blacklist;
    $scope.whitelist = $callerScope.whitelist;
    $scope.selectedBlack = [];
    $scope.selectedWhite = [];

    $scope.close = function(){
        dialog.close();
    };

    $scope.edit = function(){
        $callerScope.blacklistIds = $scope.blacklistIds;
        dialog.close();
        $http.post('/api/blacklist', {
            blacklist:$scope.blacklistIds
        })
    };

    $scope.allWhite = function() {
        $scope.whitelist = $scope.users;
        $scope.blacklist = [];
        $scope.blacklistIds = [];
        $scope.selectedBlack = [];
    }

    $scope.allBlack = function() {
        $scope.blacklist = $scope.users;
        $scope.whitelist = [];
        $scope.blacklistIds = $scope.blacklist.map(function (item) {
            return item.id;
        });
        $scope.selectedWhite = [];
    }

    $scope.selectedToWhite = function() {
        for (i = 0; i < $scope.selectedBlack.length; i++) {
            delete $scope.blacklistIds[$scope.blacklistIds.indexOf(
                    $scope.selectedBlack[i])];
        }

        updateLists($scope);
        $scope.selectedBlack = [];
    }

    $scope.selectedToBlack = function() {
        for (i = 0; i < $scope.selectedWhite.length; i++) {
            $scope.blacklistIds[$scope.blacklistIds.length] =
                    $scope.selectedWhite[i];
        }

        updateLists($scope);
        $scope.selectedWhite = [];
    }
});
