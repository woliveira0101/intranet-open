function updateLists($scope) {
    $scope.whitelist = _.filter($scope.users, function(user){
       return $scope.blacklistIds.indexOf(user.id) < 0;
    });
    $scope.blacklist = _.filter($scope.users, function(user){
       return $scope.blacklistIds.indexOf(user.id) >= 0;
    });
}

App.controller('wstalCtrl', function($scope, $http, $dialog) {
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

    $scope.show_box = false;

    $http.get('/api/users').success(function(data){
        $scope.users = data.users;
    });

    $http.get('/api/presence').success(function(data){
        $scope.lates = data.lates;
        $scope.absences = data.absences;
        $scope.blacklistIds = data.blacklist;
    });


    $scope.get_lates = function(){
        return _.filter($scope.lates, function(user){
           return $scope.blacklistIds.indexOf(user.id) < 0;
        });
    };

    $scope.get_absences = function(){
        return _.filter($scope.absences, function(user){
           return $scope.blacklistIds.indexOf(user.id) < 0;
        });
    };


    $scope.show = function(){
        $scope.show_box = !$scope.show_box;
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

App.controller('blackListCtrl', function($scope, $http, $timeout, dialog, $callerScope) {
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
            delete $scope.blacklistIds[$scope.blacklistIds.indexOf($scope.selectedBlack[i])];
        }

        updateLists($scope);
        $scope.selectedBlack = [];
    }

    $scope.selectedToBlack = function() {
        for (i = 0; i < $scope.selectedWhite.length; i++) {
            $scope.blacklistIds[$scope.blacklistIds.length] = $scope.selectedWhite[i];
        }

        updateLists($scope);
        $scope.selectedWhite = [];
    }
});
