var App = angular.module('teams', ['ngDragDrop', 'ui.bootstrap']);

App.controller('oneCtrl', function($scope, $dialog) {
  $scope.teams = [
    {
      id: 1,
      name: 'Team 1',
      users: [],
      img: 'static/t1.jpg'
    },
    {
      id: 2,
      name: 'Team 2',
      users: [],
      img: 'static/t2.jpg'
    },
    {
      id: 3,
      name: 'Team 3',
      users: [],
      img: 'static/t3.jpg'
    },
    {
      id: 4,
      name: 'Team 4',
      users: [],
      img: 'static/t4.jpg'
    }
  ];

  $scope.users = [
    {
      id: 1,
      name: 'Konrad Rotkiewicz',
      img: 'static/u1.png'
    },
    {
      id: 2,
      name: 'Adam Bendynski',
      img: 'static/u2.png'
    },
    {
      id: 3,
      name: 'Marcin Skoczylas',
      img: 'static/u1.png'
    },
    {
      id: 4,
      name: 'Wojtek Lichota',
      img: 'static/u2.png'
    },
    {
      id: 5,
      name: 'Mariusz Osiecki',
      img: 'static/u1.png'
    },
    {
      id: 6,
      name: 'Tomasz Garbarczyk',
      img: 'static/u2.png'
    },
    {
      id: 7,
      name: 'Krzysiek Witkowski',
      img: 'static/u1.png'
    },
    {
      id: 8,
      name: 'Waldemar Stal',
      img: 'static/u2.png'
    },
    {
      id: 9,
      name: 'Wojtek Lichota',
      img: 'static/u2.png'
    },
    {
      id: 10,
      name: 'Mariusz Osiecki',
      img: 'static/u1.png'
    },
    {
      id: 11,
      name: 'Tomasz Garbarczyk',
      img: 'static/u2.png'
    },
    {
      id: 12,
      name: 'Krzysiek Witkowski',
      img: 'static/u1.png'
    },
    {
      id: 13,
      name: 'Waldemar Stal',
      img: 'static/u2.png'
    },
    {
      id: 14,
      name: 'Marcin Skoczylas',
      img: 'static/u1.png'
    },
    {
      id: 15,
      name: 'Wojtek Lichota',
      img: 'static/u2.png'
    },
    {
      id: 16,
      name: 'Mariusz Osiecki',
      img: 'static/u1.png'
    },
    {
      id: 17,
      name: 'Tomasz Garbarczyk',
      img: 'static/u2.png'
    },
    {
      id: 18,
      name: 'Krzysiek Witkowski',
      img: 'static/u1.png'
    },
    {
      id: 19,
      name: 'Waldemar Stal',
      img: 'static/u2.png'
    },
    {
      id: 20,
      name: 'Wojtek Lichota',
      img: 'static/u2.png'
    },
    {
      id: 21,
      name: 'Mariusz Osiecki',
      img: 'static/u1.png'
    },
    {
      id: 22,
      name: 'Tomasz Garbarczyk',
      img: 'static/u2.png'
    },
    {
      id: 23,
      name: 'Krzysiek Witkowski',
      img: 'static/u1.png'
    },
    {
      id: 24,
      name: 'Waldemar Stal',
      img: 'static/u2.png'
    }
  ];

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
      d.open('static/team.html', 'teamCtrl');
  };

  $scope.save = function(team){
    team.dirty = false;
  };

  $scope.delete = function (item, team){
    var index = team.users.indexOf(item);
    team.users.splice(index, 1);
    team.dirty = true;
  };

});

App.controller('teamCtrl', function($scope, dialog, $callerScope, team) {
  $scope.team = angular.copy(team || {users:[], name: ''});

  $scope.add = function(){
    $scope.form_submitted = true;
    if($scope.teamForm.$invalid) return;

    $scope.team.id = 5;
    $callerScope.teams.push($scope.team);

    dialog.close();
  };

  $scope.edit = function(){
    $scope.form_submitted = true;
    if($scope.teamForm.$invalid) return;

    team.name = $scope.team.name;

    dialog.close();
  };

  $scope.close = function(){
    dialog.close();
  }
});
$(function() {
    $.fn.hasScrollBar = function() {
        return this.get(0).scrollHeight > this.height();
    }
    setTimeout(function() {
      var teams = $('.team-box ul'),
          users = $('.box-users ul'),
          scrollTeams = teams.hasScrollBar(),
          scrollUsers = users.hasScrollBar();
      if (scrollTeams) {
        teams.addClass('scroll');
      }
      if (scrollUsers) {
        users.parent().addClass('scroll-user');
      }
    }, 1000);
});