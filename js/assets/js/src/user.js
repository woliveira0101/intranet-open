App = angular.module('intranet');

App.controller('usersCtrl', function($scope, $http, $dialog, $timeout) {
    $scope.users = [];
    $scope.filtered_out_users = [];
    $scope.search = {
      name: '',
      start_work: null,
      stop_work: null,
      locations: [],
      group:[],
      team: []
    };
    $scope.location=[
        {
            id:'poznan',
            name:'Poznań'
        },{
            id:'wroclaw',
            name:'Wrocław'
        }
    ];
    $scope.groups = [
        {
            id:'1',
            name:'INTERN'
        },{
            id:'2',
            name:'P1'
        },{
            id:'4',
            name:'P2'
        },{
            id:'8',
            name:'P3'
        },{
            id:'16',
            name:'P4'
        },{
            id:'32',
            name:'FED'
        },{
            id:'64',
            name:'ADMIN'
        },{
            id:'128',
            name:'Expert zew.'
        },{
            id:'258',
            name:'Android Dev'
        },{
            id:'512',
            name:'Tester'
        },{
            id:'1024',
            name:'CEO\'s Assistant'
        },{
            id:'2048',
            name:'CEO'
        },{
            id:'user',
            name:'user'
        },{
            id:'coordinator',
            name:'coordinator'
        },{
            id:'scrum',
            name:'scrum'
        },{
            id:'cron',
            name:'cron'
        },{
            id:'admin',
            name:'admin'
        }
    ];


    $http.get('/api/users?full=1').success(function(data){
           $scope.users = data;
    });

    $http.get('/api/teams').success(function(data){
        $scope.teams = data;
        $scope.teams_to_user = {};
        _.each(data, function(team){
            $scope.teams_to_user[team['id']] = team['users'];
        });
        $scope.search.team = [1]; <!--szczuczka aby wymusić odświeżenie -- spowodowane kiepska implementacja dyrektywy bs-select  -->
        $timeout(function(){
            $scope.search.team = [];
        }, 0);
    });

    $scope.employees = function(){
        return _.filter($scope.users, function(user){
            if (user.is_active)
                return user;
        });
    };
});


App.filter('my_filter', function() {
    return function(users, my_form, teams_to_user) {
        return _.filter(users, function(user){
            debugger;
            if ((((user.name.toLowerCase()).indexOf(my_form.name.toLowerCase())) != -1) &&
                (!my_form.start_work || (Date.parseExact(user.start_work, "d/M/yyyy") < my_form.start_work)) &&
                (!my_form.stop_work || (new Date(user.stop_work) < my_form.stop_work)) &&
                (my_form.locations.length == 0 || (my_form.locations.indexOf(user.location) != -1)) &&
                (my_form.team.length == 0 || _.some(my_form.team, function(one_team){return (teams_to_user[one_team] && teams_to_user[one_team].indexOf(user.id) != -1)}))&&
                (my_form.group.length == 0 || (_.intersection(user.groups, my_form.group)).length > 0)
                )
                return user;
        });
    }
  });