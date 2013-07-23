New release
===========

- change date format in log names
- bugfix: add default project for bugs in sprint

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

0.8 (23-04-2013)
===============

- expected monthly worked hours in /times/report/pivot fix
- current user always should be at the top of list in /times/report/pivot
- add Definition of Done, Working agreement and Continuous Integration Url to project.
- add support for blocked bugs in sprints (bugzilla only)
- support for fractions as scrum points
- scrum: bug is closed when has status VERIFIED
