var App = angular.module('intranet');

App.run(function($rootScope) {
  $rootScope.G = G;
});

var calculateHeight = function() {
  maxHeight = $(window).height();
  $('.frame_team').css('max-height', maxHeight - 50);
  $('.frame_team ul').css('max-height', maxHeight - 215);
  $('.frame_team .box').css('max-height', maxHeight - 50);
  $('.team-box > ul').css('max-height', maxHeight - 248);
};
$( window ).resize(function() {
  calculateHeight();
});

$.fn.hasScrollBar = function() {
  return this.get(0).scrollHeight > this.height();
};

var resetScrolls = function(){
  var teams = $('.team-box ul');
  var users = $('.box-users ul');
  var scrollTeams = teams.hasScrollBar();
  var scrollUsers = users.hasScrollBar();

  calculateHeight();

  if (scrollTeams) {
    teams.addClass('scroll');
  }
  if (scrollUsers) {
    users.parent().addClass('scroll-user');
  }
};

var getTimeTicketsReportUrl = function(projectId, previousMonth) {
  var endDate = new Date();
  endDate.setMonth(endDate.getMonth() + 1);
  endDate.setDate(0);
  if (previousMonth) {
    endDate.setDate(0);
  }
  startDate = new Date();
  startDate.setMonth(endDate.getMonth());
  startDate.setDate(1);

  params = {
    date_range: startDate.toString('dd-MM-yyyy')
                + '+-+' + endDate.toString('dd-MM-yyyy'),
    projects: projectId,
    group_by_client: 'y',
    group_by_project: 'y',
    group_by_bugs: 'y',
    group_by_user: 'y'
  }
  url = '/times/tickets/report?';
  for (key in params) {
    url += key + '=' + params[key] + '&';
  }
  return url;
}

App.controller('oneCtrl', function($scope, $http, $dialog, $timeout, $filter) {
  $scope.teams = [];
  $scope.users = [];
  $scope.teamless = false;
  $scope.show_users = false;

  $scope.thisMonthWorkedHoursTooltip = 'Numbers of hours spent on this project <i>this</i> month';
  $scope.lastMonthWorkedHoursTooltip = 'Numbers of hours spent on this project <i>last</i> month';

  $http.get('/api/users').success(function(data){
    $scope.users = data.users;

    $http.get('/api/teams').success(function(data){
      $scope.teams = data.teams;
      _.each($scope.teams, function(team){
        team.workedHoursLastMonth = 0;

        _.each(team.projects, function(project){
          project.monthTimesUrl = getTimeTicketsReportUrl(project.id, false);
          project.previousMonthTimesUrl = getTimeTicketsReportUrl(project.id, true);
          team.workedHoursLastMonth += project.last_month_worked_hours;
          project.last_month_worked_hours = Math.round(project.last_month_worked_hours);
          project.this_month_worked_hours = Math.round(project.this_month_worked_hours);
        });

        team.projects = $filter('orderBy')(team.projects, 'last_month_worked_hours', true).slice(0, 4); // only top 4 projects

        team.users = _.filter($scope.users, function(user){
          return team.users.indexOf(user.id) !== -1;
        });

      });
      resetScrolls()
    });
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
    $('.tooltip').remove();
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

  $scope.toggle_users = function(){
    $scope.show_users = !$scope.show_users;
    if($scope.show_users){
      $timeout(resetScrolls, 100);
    }
  };

  $scope.get_users = function(){
    if(!$scope.teamless){
      return $scope.users;
    }
    var users_in_teams = _.flatten(_.map($scope.teams, function(team){
      return team.users;
    }));
    return _.filter($scope.users, function(user){
      return _.indexOf(users_in_teams, user) === -1;
    });
  };

  $scope.get_filtered_users = function(){
    return $filter('filter')($scope.get_users(), 'userSearch');
  };

});

App.controller('teamCtrl', function($scope, $http, $timeout, dialog, $callerScope, team) {
  $scope.team = angular.copy(team || {users:[], name: '', img: '/api/preview?type=team'});
  $scope.swap_with_preivew = false;

  $scope.add = function(){
    $scope.form_submitted = true;
    if($scope.teamForm.$invalid) return;

    $http.post('/api/teams', {
      name: $scope.team.name,
      swap_with_preview: true
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
