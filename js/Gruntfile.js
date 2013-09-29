var FILES = require('./assets.js');

module.exports = function(grunt) {

  // Project configuration.
  grunt.initConfig({
    pkg: grunt.file.readJSON('package.json'),
    clean: {
      options: {
        force: true
      },
      src: [
        FILES['STATIC'] + 'js',
        FILES['STATIC'] + 'css'
      ]
    },
    copy: {
      jquery_ui: {
          expand: true,
          cwd: FILES['JQUERY_UI'],
          src: '**',
          dest: FILES['STATIC'] + 'css/images'
      }
    },
    ngmin: {
      app: {
        src: FILES['APP_JS'],
        dest: FILES['NGMINNED_APP']
      }
    },
    concat: {
      vendor_js: {
        options: {
          separator: '\n;\n'
        },
        src: FILES['VENDOR_JS'],
        dest: FILES['STATIC'] + '/js/vendor.js'
      },
      app_js: {
        src: FILES['APP_JS'],
        dest: FILES['STATIC'] + '/js/app.js'
      }
    },
    uglify: {
      options: {
        compress: {}
      },
      vendor: {
        src: FILES['VENDOR_JS'],
        dest: FILES['STATIC'] + '/js/vendor.js'
      },
      app: {
        // we have to run ngmin first
        src: FILES['NGMINNED_APP'],
        dest: FILES['STATIC'] + '/js/app.js'
      }
    },
    recess: {
      concat: {
        options: {
          compile: true
        },
        src: FILES['VENDOR_CSS'].concat(FILES['APP_LESS']),
        dest: FILES['STATIC'] + '/css/app.css'
      },
      // recess:compress minifies the resulting css, too - production
      compress: {
        options: {
          compile: true,
          compress: true
        },
        src: FILES['VENDOR_CSS'].concat(FILES['APP_LESS']),
        dest: FILES['STATIC'] + '/css/app.css'
      }
    },
    watch: {
      js: {
        files: FILES['APP_JS'].concat(FILES['PARTIALS_SRC']),
        tasks: 'concat'
      },
      less: {
        files: FILES['APP_LESS'],
        tasks: 'recess:concat'
      }
    },
    ngtemplates: {
      intranet: {
         options:    {
           base: 'assets/partials',
           htmlmin: {}
         },
         src: FILES['PARTIALS_SRC'],
         dest: FILES['PARTIALS_DEST']
      }
    }
  });

  // Load the plugin that provides the "uglify" task.
 // Grunt modules
  grunt.loadNpmTasks('grunt-contrib-uglify');
  grunt.loadNpmTasks('grunt-contrib-copy');
  grunt.loadNpmTasks('grunt-contrib-concat');
  grunt.loadNpmTasks('grunt-contrib-watch');
  grunt.loadNpmTasks('grunt-contrib-clean');
  grunt.loadNpmTasks('grunt-ngmin');
  grunt.loadNpmTasks('grunt-recess');
  grunt.loadNpmTasks('grunt-angular-templates');

  // Default task(s).
  grunt.registerTask('dev', ['clean', 'ngtemplates', 'concat', 'recess:concat', 'copy:jquery_ui', 'watch']);
  grunt.registerTask('prod', ['clean', 'ngtemplates', 'ngmin', 'recess:compress', 'copy:jquery_ui', 'uglify']);

};
