var App = angular.module('intranet');


App.controller('sprintEditCtrl', function($scope) {
  if(board){
    $scope.columns = board;
  } else {
    $scope.columns = [{name: 'example name', sections: [{name: 'example name', cond: ''}]}];
  }

  $scope.columns_json = function(){
    return angular.toJson($scope.columns);
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
