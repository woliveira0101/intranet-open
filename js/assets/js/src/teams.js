var App = angular.module('intranet', ['ngDragDrop', 'ui.bootstrap']);
$.fn.hasScrollBar = function() {
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
      d.open('team.html', 'teamCtrl');

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

App.controller('teamCtrl', function($scope, $http, $timeout, dialog, $callerScope, team) {
  $scope.team = angular.copy(team || {users:[], name: '', img: '/api/images/teams/0'});
  $scope.swap_with_preivew = false;

  $scope.add = function(){
    $scope.form_submitted = true;
    if($scope.teamForm.$invalid) return;

    $http.post('/api/teams', {
      name: $scope.team.name,
      swap_with_preview: $scope.swap_with_preivew
    }).success(function(data){
        $scope.team.id = data.id;
        $scope.team.img = data.img;
        $callerScope.teams.push($scope.team);
        dialog.close();
    });
  };

  $scope.edit = function(){
    $scope.form_submitted = true;
    if($scope.teamForm.$invalid) return;

    $http.put('/api/teams/' + team.id, {
      name: $scope.team.name,
      swap_with_preview: $scope.swap_with_preivew
    }).success(function(data){
        team.name = $scope.team.name;
        team.img = team.img + '?t=' + (new Date().getTime());
        dialog.close();
    });

  };

  $scope.close = function(){
    dialog.close();
  };

  $timeout(function(){
    var $btn = $('#upload-btn');

    var up = new Uploader($btn, {
      url: '/api/preview?type=team',
      onLoad: function(e) {
        $('#my-avatar img').attr('src',e.file.url+'?t='+(new Date().getTime()));
      },
      onComplete: function(e) {
        $scope.swap_with_preivew = true;
        $scope.$apply();
      },
      onProgress: function(e) {},
      onAdd: function(e) {},
      onError: function(e) {}
    });

  }, 100);

  return false;

});
