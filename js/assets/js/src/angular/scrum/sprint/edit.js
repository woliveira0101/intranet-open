var App = angular.module('intranet');


App.controller('sprintEditCtrl', function($scope, $http, $dialog) {
  $scope.sprintId = sprint_id;

  if(board_full_data && board_full_data['board'].length){
    $scope.columns = board_full_data['board'];
  } else {
    $scope.columns = [{name: '', sections: [{name: '', cond: ''}]}];
  }

  if (board_full_data && board_full_data['colors'].length) {
    $scope.colors = board_full_data['colors'];
  } else {
    $scope.colors = [
      {color: '#FFFFFF', cond: '', name: 'Color name'}
    ];
  }

  $scope.columns_json = function(){
    var boards = {
      'board': $scope.columns,
      'colors': $scope.colors
    }

    return angular.toJson(boards);
  };

  $scope.save = function(){
    var name = prompt('Name');
    var data = {
      'name': name,
      'board': angular.toJson($scope.columns)
    };
    $http.post('/api/boards', data);
  };

  $scope.add_column = function(){
    $scope.columns.push({name: '', sections: [{name: '', cond: ''}]})
  };

  $scope.add_section = function(column){
    column.sections.push({name: '', cond: ''})
  };

  $scope.remove_column = function(column){
    var index = $scope.columns.indexOf(column);
    $scope.columns.splice(index, 1);
  };

  $scope.remove_section = function(section, sections){
    var index = sections.indexOf(section);
    sections.splice(index, 1);
  };

  $scope.show_bugs = function(){
    var d = $dialog.dialog();
    d.open('scrum/sprint/bugsJson.html', 'sprintBugsJsonCtrl');

  };
  $scope.show_boards = function(){
    var d = $dialog.dialog({
      resolve: {
        $callerScope: function() {return $scope}
      }
    });
    d.open('scrum/sprint/boards.html', 'sprintBoardsCtrl');

  };

  $scope.add_color = function () {
    $scope.colors.push({color: '#FFFFFF', cond: ''})
  };

  $scope.remove_color = function (color) {
    var index = $scope.colors.indexOf(color);
    $scope.colors.splice(index, 1);
  };

});

App.controller('sprintBoardsCtrl', function($scope, $http, dialog, $dialog, $filter, $callerScope){
  $scope.selected_board = undefined;

  $http.get('/api/boards').success(function(data){
    $scope.boards = data.boards;
    $scope.only_my = true;
    if($scope.boards.length > 0){
      $scope.selected_board = $scope.get_boards()[0];
    }
  });

  $scope.clone = function(){
    $callerScope.columns = angular.fromJson($scope.selected_board.board);
    $scope.close();
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

  $scope.close = function() {
    dialog.close();
  };

  $scope.get_boards = function(){
    var boards = $scope.boards;
    if($scope.only_my){
      boards = _.filter(boards, function(b){
        return b.user.id == $scope.G.user.id;
      });
    }
    return boards
  };

  $scope.get_name = function(board){
    if($scope.only_my || board.user.id == $scope.G.user.id){
      return ''
    } else {
      return ' ( ' + board.user.name + ' )'
    }
  };
});

App.controller('sprintBugsJsonCtrl', function($scope, $http, dialog, $dialog){
  var promise = $http.get('/api/sprint/' + sprint_id + '/bugs')
  promise.success(function(response){
    $scope.bugs = JSON.stringify(angular.fromJson(response), undefined, 4);
  });

  $scope.bugs_error = false;
  promise.error(function(response){
    $scope.bugs_error = true
  });

  $scope.close = function() {
    dialog.close();
  };
});
