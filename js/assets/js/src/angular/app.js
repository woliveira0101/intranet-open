var App = angular.module('intranet', ['ngDragDrop', 'ui.bootstrap', '$strap.directives']);

App.run(function($rootScope) {
  $rootScope.G = G;
});
