angular.module('$strap.directives').directive('userTooltip', [
  '$parse',
  '$compile',
  function ($parse, $compile) {
    return {
      restrict: 'A',
      scope: true,
      link: function postLink(scope, element, attrs, ctrl) {
        user = $parse(attrs.userTooltip)(scope),

        element.tooltip({
          title: '<h3>' + user.name + '</h3>Ładowanie...',
          html: true,
          // delay: 300,
          animation: false,
          placement: 'bottom',
          template: '"<div class="tooltip users-tooltip-container"><div id="users-tooltip-angular" class="tooltip-inner"></div></div>"'
        });
        var tooltip = element.data('tooltip');

        scope.users = {};
        scope.xhr = null;
        scope.get = function(uid,fn){
          if(scope.xhr){
              scope.xhr.abort();
          }
          if(uid in scope.users){
              fn(scope.users[uid]);
          }else{
              scope.xhr = $.get('/user/tooltip?user_id='+uid,function(html){
                  scope.xhr = null;
                  scope.users[uid] = html;
                  fn(html);
              });
          }
        };

        scope.userId = user.id;
        element.mouseenter(function () {
          if (!(scope.userId in scope.users)) {
            scope.get(scope.userId, function(html){
              tooltip.options.title = html;
              tooltip.setContent();
              if (tooltip.hoverState == 'in') {
                tooltip.show();
              }
            });
          }
        })
      }
    };
  }
]);