var App = angular.module('intranet');


App.controller('sprintEditCtrl', function($scope, $http) {
  if(board){
    $scope.columns = board;
  } else {
    $scope.columns = [{name: 'example name', sections: [{name: 'example name', cond: ''}]}];
  }

  $scope.columns_json = function(){
    return angular.toJson($scope.columns);
  };


  $scope.selected_board = {
    'name': '-----------',
    'board': $scope.columns_json()
  };

  $http.get('/api/boards').success(function(data){
    $scope.boards = data.boards;
    $scope.boards.push($scope.selected_board);
    $scope.boards.reverse();
  });

  $scope.choose = function(){
    $scope.columns = angular.fromJson($scope.selected_board.board);
  };

  $scope.delete = function(){
    var r = confirm("Press a button!");
    if(r === true){
      $http.delete('/api/boards/' + $scope.selected_board.id).success(function(){
        var index = $scope.boards.indexOf($scope.selected_board);
        $scope.boards.splice(index, 1);
        $scope.selected_board = $scope.boards[0];
      });
    }
  };

  $scope.save = function(){
    var name = prompt('Name');
    var data = {
      'name': name,
      'board': angular.toJson($scope.columns)
    };

    $http.post('/api/boards', data).success(function(response){
      data.id = response.id;
      debugger;
      $scope.boards.push(data);
    });
  };

  $scope.add_column = function(){
    $scope.columns.push({name: 'example name', sections: [{name: 'example name', cond: ''}]})
  };

  $scope.add_section = function(column){
    column.sections.push({name: 'example', cond: ''})
  };

  $scope.remove_column = function(column){
    var index = $scope.columns.indexOf(column);
    $scope.columns.splice(index, 1);
  };

  $scope.remove_section = function(section, sections){
    var index = sections.indexOf(section);
    sections.splice(index, 1);
  }
});
