var App = angular.module('intranet', ['ngDragDrop', 'ngRoute', 'ui.bootstrap', '$strap.directives']);

App.config(function($httpProvider, $routeProvider, $locationProvider) {
  $httpProvider.defaults.headers.common['X-Requested-With'] = 'XMLHttpRequest';

  $routeProvider.when('/mobile/lateness', {
    templateUrl: 'lateness.html',
    controller: 'latenessCtrl',
    resolve: {
      dialog: function() {return undefined;}
    }
  }).when('/mobile/user/list', {
    templateUrl: 'users-mobile.html',
    controller: 'usersCtrl'
  }).when('/mobile/confirm', {
    template: '<div ng-bind-html="message"></div>',
    controller: 'modalConfirmCtrl',
    resolve: {
      dialog: function() {return undefined;},
      messages: function($routeParams) {return $routeParams;}
    }
  }).otherwise({
      redirectTo: '/mobile/user/list'
  });
});

App.run(function($rootScope) {
  $rootScope.G = G;
});
