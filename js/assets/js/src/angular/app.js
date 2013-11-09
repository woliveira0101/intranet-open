var App = angular.module('intranet', ['ngDragDrop', 'ui.bootstrap', '$strap.directives']);

App.config(function($httpProvider){
  $httpProvider.defaults.headers.common['X-Requested-With'] = 'XMLHttpRequest';
});

App.run(function($rootScope) {
  $rootScope.G = G;
});
