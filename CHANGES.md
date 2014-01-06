0.9.6 (28-11-2013)
===========
- better mobile support
- project configuration allows to add custom tabs in sprint with embedded iframe
- user date of birth

0.9.5 (17-11-2013)
===============
- much better scrum board layout 
- extra links to /times/tickets/report
- better out of office form
- angular sortby polish chart support
- no team option for user list
- note presence only for views, not api 
- teams page visible for users
- bug fixes

0.9.4 (14-11-2013)
===============
- absence / lates enhancemets
- more teams enhancemets
- more users list enhancements
- velocity per day
- fixes for github fetcher
- bugzilla sprint regex fix
- user avatar edit fix
- better project filter in client/project view

0.9.3 (24-09-2013)
===============
- absence / lates support 
- teams enhancemets
- users list enhancements

0.9.2 (24-09-2013)
===============
- show active sprints by default
- illnes absence only avaliable for employment contract employee
- avatar upload button fix
- teams tab avaliable for client, add tooltip to user there
- scrum user has ability to edit scrum fields in project
- github support for scrum board

0.9.1 (12-09-2013)
===============
- better scrum board column mapping for pivotaltracker

0.9.0 (09-09-2013)
===============
- support for multiproject sprints
- add basic REST API (bugs and times endpoints disabled)
- Grunt for assets controling
- better IP control (now you can specify range like '192.168.1.1 - 192.168.1.120'
- removed organic tabs
- add basic teams feature 
- add github connector
- freelancer unification
- now user in group scrum can add sprints
- client's & project's active field 

- fix for sprint points for pivotaltracker
- client's backlog fix

(')

0.8.12 (12-08-2013)
===============
- unfuddle connector enhancements and fixes
- better multi user and multi project selector

0.8.11 (05-08-2013)
===============

- email as a user identifier in Export hours per Client By Employee
- project_id -> project_name mapping for unfuddle connector
- component_id -> component_name mapping for unfuddle connector
- add component name to unfuddle bug
- change twisted web server combined log to be daily rotated
- support multiple project for PivotalTracker

0.8.10 (29-07-2013)
===============

- fixes to Export hours per Client By Employee
- add scrum support for Pivotal Tracker

0.8.9 (24-07-2013)
===============

- change date format in log names
- bugfix: add default project for bugs in sprint
- export Export hours per Client By Employee (excel)

0.8.8 (15-07-2013)
===============

- typeahead for project(s) selectors
- better old bugs report
- absence table enhancements
- new filter options for sprint times

0.8.7 (04-07-2013)
===============

- better sorting for /times/report/pivot and /employees/table/absences
- color fixes for /employees/table/absences

0.8.6 (28-06-2013)
===============

- more fixes to absence view
- better /times/report/pivot
- scrum role fix

0.8.5 (18-06-2013)
===============

- fixes to absence view
- minor fixes everywhere

- add absences view

0.8.4 (06-06-2013)
===============

- add absences view


0.8.3 (03-06-2013)
===============

- scrum board enhancements
- minor bug fixes
- add installation guide to README.md
- add next sprint and prev sprint buttons
- add meetings filter in Time entries report
- add bigger than field in Time entries
- custom twistd launcher - add daily log rotation
- grouping feature in Time entries to excel
- scrum board as a main tab
- add new group: scrum (ability to add/edit/delete sprints)

0.8.2 (13-05-2013)
===============

- minor fixes
- scrum board redesign (version 1.0)
- add retrospective notes

0.8.1 (07-05-2013)
===============

- add times tab to sprint view
- tablesorter in time entries views i.e. /times/tickets/report
- add bug sprint time in /scrum/sprint/show
- counting achieved points fix
- add velocity per bug
- add absence pivot link
- tab /employees/list/late translated to english
- remove some spreadsheets field (new.sql to db migrate)
- Intranet logo is red when develop mode
- removed jinja filters dependency with config file
- daily presence splited into Poznan and Wroclaw
- sprint layout slighty changed
- fixed client add bug
- modify client map columns
- modify velocity per bug - count when closed or verified

0.8 (23-04-2013)
===============

- expected monthly worked hours in /times/report/pivot fix
- current user always should be at the top of list in /times/report/pivot
- add Definition of Done, Working agreement and Continuous Integration Url to project.
- add support for blocked bugs in sprints (bugzilla only)
- support for fractions as scrum points
- scrum: bug is closed when has status VERIFIED
