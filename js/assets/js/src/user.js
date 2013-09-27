App = angular.module('intranet');

App.controller('usersCtrl', function($scope, $http, $dialog) {
    $scope.users = [];
    $scope.user = '';
    $scope.filtered_out_users = [];
    $scope.search = {
      name: '',
      start_work: null,
      stop_work: null,
      locations: [],
      group:'',
      team: []
    };

    $scope.location=[
        {
            id:'poznan',
            name:'Poznań'
        },
        {
            id:'wroclaw',
            name:'Wrocław'
        }
    ]

    $scope.groups = [
            ('1', 'INTERN'),
            ('2', 'P1'),
            ('4', 'P2'),
            ('8', 'P3'),
            ('16', 'P4'),
            ('32', 'FED'),
            ('64', 'ADMIN'),
            ('128', 'Expert zew.'),
            ('256', 'Android Dev'),
            ('512', 'Tester'),
            ('1024', 'CEO\'s Assistant'),
            ('2048', 'CEO'),
            ('user', 'user'),
            ('coordinator', 'coordinator'),
            ('scrum', 'scrum'),
            ('cron', 'cron'),
            ('admin', 'admin'),
        ]

//    $scope.teams = function(){
//        var teames = []
//        for (var i = 0; i< $scope.users.length ; i++){
//            debugger;
//            teames = _.union(teames,$scope.users[i].team);
//        };
//        return teames;
//
//    };

    $http.get('/api/users?full=1').success(function(data){
           $scope.users = data;
    });

    $http.get('/api/teams').success(function(data){
        $scope.teams = data;
    });

    $scope.employees = function(){
        return _.filter($scope.users, function(user){
            if (user.is_active)
                return user;
        });
    };

    $scope.filter = function(){
        var user;
        if($scope.filtered_out_users.length > 0){
            user = $scope.filtered_out_users.splice(0, 1)[0];
            $scope.users.push(user);
        } else {
            user = $scope.users.splice(0, 1)[0];
            $scope.filtered_out_users.push(user);
        }
    };



});
App.filter('my_filter', function() {
    return function(users, my_form) {
        return _.filter(users, function(user){
            if ((((user.name.toLowerCase()).indexOf(my_form.name.toLowerCase())) != -1) &&
                (!my_form.start_work || (Date.parseExact(user.start_work, "d/M/yyyy") < my_form.start_work)) &&
                (!my_form.stop_work || (new Date(user.stop_work) < my_form.stop_work)) &&
                (my_form.locations.length == 0 || (my_form.locations.indexOf(user.location) != -1)) &&
                (!my_form.team.length == 0)
                )
                return user;
        });
    }
  });