App.controller('usersCtrl', function($scope, $http, $dialog, $timeout) {
    $scope.users = [];
    $scope.tab = 'employees';
    $scope.search = {
      name: '',
      start_work: '',
      stop_work: '',
      locations: [],
      roles: [],
      teams: []
    };

    $scope.locations = [
        {
            id:'poznan',
            name:'Poznań'
        },
        {
            id:'wroclaw',
            name:'Wrocław'
        }
    ];
    $scope.set_tab = function(name){
       $scope.tab = name;
    };

    $scope.roles = _.map(G.ROLES, function(role){
      return {id: role[0], name: role[1]};
    });

    $scope.to_pretty_role = function(role){
      return _.find(G.ROLES, function(a_role){
        return a_role[0] === role;
      })[1];
    };

    $http.get('/api/users?full=1&inactive=1').success(function(data){
      $scope.users = data.users;
      $http.get('/api/teams').success(function(data){
        $scope.teams = data.teams;
        $scope.teams_to_user = {};
        $scope.user_to_teams = {};
        _.each(data, function(team){
          $scope.teams_to_user[team['id']] = team['users'];
        });

        _.each($scope.users, function(user){
          user.teams = [];
          _.each($scope.teams, function(team){
            if(team.users.indexOf(user.id) >= 0){
             user.teams.push(team.id);
            }
          });
        });

        $scope.search.teams = [1]; <!--szczuczka aby wymusić odświeżenie -- spowodowane kiepska implementacja dyrektywy bs-select  -->
        $timeout(function(){
          $scope.search.teams = [];
        }, 0);
      });
    });


    $scope.filtered_users = function(){
      var filtered_users = $scope.users;

      filtered_users = _.filter(filtered_users, function(user){
        var f_name = $scope.search.name.toLowerCase();
        var u_name = user.name.toLowerCase();
        return u_name.indexOf(f_name) >= 0;
      });

      filtered_users = _.filter(filtered_users, function(user){
        var f_roles = $scope.search.roles;
        var u_roles = user.roles;
        var intersection = _.intersection(f_roles, u_roles);
        return f_roles.length === intersection.length;
      });

      filtered_users = _.filter(filtered_users, function(user){
        var f_locations = $scope.search.locations;
        var u_location = user.location[0];
        return f_locations.length === 0 || _.indexOf(f_locations, u_location) >= 0;
      });

      filtered_users = _.filter(filtered_users, function(user){
        var f_teams = $scope.search.teams;
        var u_teams = user.teams;
        var intersection = _.intersection(f_teams, u_teams);
        return f_teams.length === intersection.length;
      });

      filtered_users = _.filter(filtered_users, function(user){
        var f_start_work = Date.parse($scope.search.start_work);
        var u_start_work = Date.parse(user.start_work);
        return !f_start_work || !u_start_work || (start = u_start_work >= f_start_work);
      });

      filtered_users = _.filter(filtered_users, function(user){
        var f_stop_work = Date.parse($scope.search.stop_work);
        var u_stop_work = Date.parse(user.stop_work);
        return !f_stop_work || !u_stop_work || u_stop_work <= f_stop_work;
      });

      return filtered_users;
    };

    $scope.get_employees = function(){
      return _.filter($scope.filtered_users(), function(user){
        var not_client = _.indexOf(user.groups, 'client') === -1;
        var not_freelancer = !user.freelancer;
        return user.is_active && not_client && not_freelancer;
      });
    };
    $scope.get_freelancers = function(){
      return _.filter($scope.filtered_users(), function(user){
        return user.is_active && user.freelancer;
      });
    };
    $scope.get_clients = function(){
      return _.filter($scope.filtered_users(), function(user){
        var client = _.indexOf(user.groups, 'client') >= 0;
        return client;
      });
    };
    $scope.get_inactive = function(){
      return _.filter($scope.filtered_users(), function(user){
        var not_client = _.indexOf(user.groups, 'client') === -1;
        return !user.is_active && not_client;
      });
    };

    $scope.get_users = function(){
      if($scope.tab === 'employees'){
        return $scope.get_employees();
      } else if ($scope.tab === 'freelancers'){
        return $scope.get_freelancers();
      } else if ($scope.tab === 'clients'){
        return $scope.get_clients();
      } else if ($scope.tab === 'inactive'){
        return $scope.get_inactive();
      }
    };
});
