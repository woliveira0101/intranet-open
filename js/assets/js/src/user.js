App = angular.module('intranet');

App.controller('usersCtrl', function($scope, $http, $dialog) {
    $scope.users = [];
    $scope.user = '';
    $scope.filtered_out_users = [];
    $scope.search = {
      name: '',
      start_work: null,
      stop_work: null,
      location: '',
      group:'',
      team: ''
    };

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
$scope.teams = [
  {
    "id": "1",
    "name": "gyhjtygj"
  },
  {
    "id": "2",
    "name": "tyjtyj"
  },
  {
    "id": "3",
    "name": "tyjty"
  }
]

    $http.get('/api/users?full=1').success(function(data){
           $scope.users = data;


    });
    $scope.employees = function(){
        return _.filter($scope.users, function(user){
            if (user.is_active)
                return user;
        });
    };

    console.log($scope.search);


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

//    $scope.my_filter = function(elem){
//        if(elem.name == 'Malwina Nowakowska'){
//            return true;
//        }
//
//    };



});
App.filter('my_filter', function() {
    return function(users, my_form) {
        return _.filter(users, function(user){
            if ((((user.name.toLowerCase()).indexOf(my_form.name.toLowerCase())) != -1) &&
                true
                )
                return user;
        });
//      if (((input.name).indexOf(my_form.name)) != 1){
//                return true;
//            }

    }
  });