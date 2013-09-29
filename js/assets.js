var BOWER_COMPONENTS = 'bower_components/';

var BOWER_JS = [
  BOWER_COMPONENTS + 'jquery/jquery.js',
  BOWER_COMPONENTS + 'jquery-ui/ui/jquery-ui.js',
  BOWER_COMPONENTS + 'bootstrap/js/bootstrap-tooltip.js',
  BOWER_COMPONENTS + 'bootstrap/js/*.js',
  BOWER_COMPONENTS + 'angular/angular.js',
  BOWER_COMPONENTS + 'angular-strap/dist/angular-strap.js',
  BOWER_COMPONENTS + 'angular-bootstrap/ui-bootstrap.min.js',
  BOWER_COMPONENTS + 'angular-bootstrap/ui-bootstrap-tpls.min.js',
  BOWER_COMPONENTS + 'datejs/build/date-en-US.js',
  BOWER_COMPONENTS + 'modernizr/modernizr.js',
  BOWER_COMPONENTS + 'underscore/underscore.js',
  BOWER_COMPONENTS + 'spectrum/spectrum.js',
  BOWER_COMPONENTS + 'bootstrap-select/bootstrap-select.js',
  BOWER_COMPONENTS + 'bootstrap-datepicker/js/bootstrap-datepicker.js',
];

var BOWER_CSS = [
  BOWER_COMPONENTS + 'jquery-ui/themes/smoothness/*.css',
  BOWER_COMPONENTS + 'spectrum/spectrum.css',
  BOWER_COMPONENTS + 'bootstrap-select/bootstrap-select.css',
  BOWER_COMPONENTS + 'bootstrap-datepicker/css/datepicker.css',
];

var STATIC = '../src/intranet3/static/';
var PARTIALS_DEST = 'tmp/partials_tmp.js';
var NGMINNED_APP = 'tmp/ngminned_app.js';

module.exports = {
   // Other vendors
  VENDOR_JS: BOWER_JS.concat([
    'assets/js/vendor/*.js'
  ]),
  VENDOR_LESS: [
    'bower_components/bootstrap/less/bootstrap.less'
  ],
  VENDOR_CSS: BOWER_CSS.concat([
    'assets/css/**/*.css'
  ]),
  JQUERY_UI: BOWER_COMPONENTS + 'jquery-ui/themes/smoothness/images',
   // Our things
  APP_JS: [
    'assets/js/src/**/*.js',
    PARTIALS_DEST
  ],
  APP_LESS: [
    'assets/less/*.less'
  ],
  NGMINNED_APP: NGMINNED_APP,
  PARTIALS_DEST: PARTIALS_DEST,
  PARTIALS_SRC: ['assets/partials/**/*.html'],
  STATIC: STATIC
};
