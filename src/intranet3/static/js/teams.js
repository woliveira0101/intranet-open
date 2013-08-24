var App = angular.module('teams', ['ngDragDrop', 'ui.bootstrap']);
$.fn.hasScrollBar = function() {
  console.log('a');
  return this.get(0).scrollHeight > this.height();
};
var resetScrolls = function(){
  var teams = $('.team-box ul'),
    users = $('.box-users ul');
  var scrollTeams = teams.hasScrollBar(),
    scrollUsers = users.hasScrollBar();
  if (scrollTeams) {
    teams.addClass('scroll');
  }
  if (scrollUsers) {
    users.parent().addClass('scroll-user');
  }
};

App.controller('oneCtrl', function($scope, $http, $dialog) {
  $scope.teams = [];
  $scope.users = [];

  $http.get('/api/users').success(function(data){
      $scope.users = data;

      $http.get('/api/teams').success(function(data){
        $scope.teams = data;
        _.each($scope.teams, function(team){
          team.users = _.filter($scope.users, function(user){
            return team.users.indexOf(user.id) !== -1;
          });
        });
      });
    resetScrolls()
  });


  $scope.onBeforeDrop = function(drop, drag){
    if(drop.indexOf(drag) !== -1) {
      return false;
    } else {
      var team = _.find($scope.teams, function(team){ return team.users == drop});
      team.dirty = true;
      return true;
    }
  };

  $scope.openModal = function(team){
      var d = $dialog.dialog({
          resolve: {
            $callerScope: function() {return $scope},
            team: function() {return team}
          }
        });
      d.open('/static/partials/team.html', 'teamCtrl');
  };

  $scope.save = function(team){
    var ids = _.pluck(team.users, 'id');
    $http.put('/api/teams/' + team.id, {
      users: ids
    }).success(function(data){
        team.dirty = false;
    });
  };

  $scope.deleteUser = function (item, team){
    var index = team.users.indexOf(item);
    team.users.splice(index, 1);
    team.dirty = true;
  };

  $scope.deleteTeam = function (team){
    var r = confirm("Press a button");
    if(r == true){
      $http.delete('/api/teams/' + team.id);
      var index = $scope.teams.indexOf(team);
      $scope.teams.splice(index, 1)
    }
  };

});

App.controller('teamCtrl', function($scope, $http, dialog, $callerScope, team) {
  $scope.team = angular.copy(team || {users:[], name: ''});

  $scope.add = function(){
    $scope.form_submitted = true;
    if($scope.teamForm.$invalid) return;

    $http.post('/api/teams', {
      name: $scope.team.name
    }).success(function(data){
        $scope.team.id = data.id;
        $callerScope.teams.push($scope.team);
        dialog.close();
    });

  };

  $scope.edit = function(){
    $scope.form_submitted = true;
    if($scope.teamForm.$invalid) return;

    $http.put('/api/teams/' + team.id, {
      name: $scope.team.name
    }).success(function(data){
        team.name = $scope.team.name;
    });

    dialog.close();
  };

  $scope.close = function(){
    dialog.close();
  }
});
