var App = angular.module('intranet', ['ngDragDrop', 'ui.bootstrap', '$strap.directives']);

App.run(function($rootScope) {
  $rootScope.G = G;
});


App.config(function($compileProvider){
  $compileProvider.urlSanitizationWhitelist(/^\s*(https?|ftp|mailto|file|tel):/);
});
