var BOWER_JS = [
  'bower_components/jquery/jquery.min.js',
  'bower_components/jquery-ui/ui/jquery-ui.js',
  'bower_components/bootstrap/js/*.js',
  'bower_components/angular/angular.js',
  'bower_components/angular-bootstrap/ui-bootstrap.min.js',
  'bower_components/angular-bootstrap/ui-bootstrap-tpls.min.js',
  'bower_components/datejs/build/date-en-US.js',
  'bower_components/modernizr/modernizr.js',
  'bower_components/underscore/underscore-min.js',
  'bower_components/spectrum/spectrum.js'
];

var STATIC = '../src/intranet3/static/';
var PARTIALS = STATIC + '/js/partials.js';

module.exports = {
   // Other vendors
  VENDOR_JS: BOWER_JS.concat([
    'assets/js/vendor/*.js'
  ]),
  VENDOR_LESS: [
    'bower_components/bootstrap/less/bootstrap.less'
  ],
   // Our things
  APP_JS: [
    'assets/js/src/**/*.js',
    PARTIALS
  ],
  APP_LESS: [
    'assets/less/*.less'
  ],
  NGMINNED_APP: 'build/ngminned/app.js',
  PARTIALS: PARTIALS,
  STATIC: STATIC
};
