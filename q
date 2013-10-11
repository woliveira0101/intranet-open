diff --git a/src/intranet3/lib/scrum/__init__.py b/src/intranet3/lib/scrum/__init__.py
index 324b573..eb9dd0b 100644
--- a/src/intranet3/lib/scrum/__init__.py
+++ b/src/intranet3/lib/scrum/__init__.py
@@ -39,7 +39,7 @@ class BugUglyAdapter(object):
     def velocity(self):
         if self.is_closed():
             points = float(self.whiteboard.get('p', 0.0))
-            return (points / self.sprint_time) if self.sprint_time else 0.0
+            return (points / self.sprint_time * 8.0) if self.sprint_time else 0.0
         return None
 
     @classmethod
diff --git a/src/intranet3/models/sprint.py b/src/intranet3/models/sprint.py
index 1b4c9dc..1981daa 100644
--- a/src/intranet3/models/sprint.py
+++ b/src/intranet3/models/sprint.py
@@ -38,5 +38,5 @@ class Sprint(Base):
 
     @property
     def velocity(self):
-        return (self.achieved_points / self.worked_hours) if self.worked_hours else 0.0
+        return (self.achieved_points / self.worked_hours * 8.0) if self.worked_hours else 0.0
 
diff --git a/src/intranet3/templates/scrum/sprint/_base_sprint.html b/src/intranet3/templates/scrum/sprint/_base_sprint.html
index 8eaf916..5fe9682 100644
--- a/src/intranet3/templates/scrum/sprint/_base_sprint.html
+++ b/src/intranet3/templates/scrum/sprint/_base_sprint.html
@@ -74,7 +74,12 @@
                             <li><span>{% trans %}Points achieved{% endtrans %}</span>{{ sprint.achieved_points }}</li>
                             <li><span>{% trans %}Points commited{% endtrans %}</span> {{ sprint.commited_points }}</li>
                             <li><span>{% trans %}Total hours{% endtrans %}</span>{{ sprint.worked_hours | round | int }}</li>
-                            <li><span>{% trans %}Velocity per hour{% endtrans %}</span>{{ '%.2f' % sprint.velocity }}</li>
+                            <li>
+                                <span>{% trans %}Velocity per day{% endtrans %}</span>
+                                <span title="This sprint velocity">{{ '%.2f' % sprint.velocity }}</span> /
+                                <span title="Mean velocity of all sprints">{{ '%.2f' % sprint.mean_velocity }}</span> /
+                                <span title="Total velocity">{{ '%.2f' % sprint.total_velocity }}</span>
+                            </li>
                         </ul>
                     </div>
                     <div class="span3">
diff --git a/src/intranet3/templates/scrum/sprint/_list.html b/src/intranet3/templates/scrum/sprint/_list.html
index d17b764..bc84cac 100644
--- a/src/intranet3/templates/scrum/sprint/_list.html
+++ b/src/intranet3/templates/scrum/sprint/_list.html
@@ -5,7 +5,7 @@
     <th>{% trans %}End{% endtrans %}</th>
     <th>{% trans %}Worked hours{% endtrans %}</th>
     <th>{% trans %}Points ( achieved / commited ){% endtrans %}</th>
-    <th>{% trans %}Velocity per hour{% endtrans %}</th>
+    <th>{% trans %}Velocity per day{% endtrans %}</th>
     {% if request.has_perm('scrum') %}
         <th>
             {% trans %}Sprint Actions{% endtrans %}
diff --git a/src/intranet3/templates/scrum/sprint/_velocity_chart.html b/src/intranet3/templates/scrum/sprint/_velocity_chart.html
index b7f25cb..3a2b2d6 100644
--- a/src/intranet3/templates/scrum/sprint/_velocity_chart.html
+++ b/src/intranet3/templates/scrum/sprint/_velocity_chart.html
@@ -8,7 +8,7 @@
         var data = google.visualization.arrayToDataTable(SPRINTS_DATA);
 
         var options = {
-            title: 'Velocity Per Hour Chart',
+            title: 'Velocity Per Day Chart',
             chartArea: {left: 50, width: '85%', top: 150},
             bar: { groupWidth: 60 },
             colors: ['#cccccc', '#1e8a31']
diff --git a/src/intranet3/views/scrum/sprint.py b/src/intranet3/views/scrum/sprint.py
index 0a39b91..9a306f3 100644
--- a/src/intranet3/views/scrum/sprint.py
+++ b/src/intranet3/views/scrum/sprint.py
@@ -122,6 +122,20 @@ class BaseSprintView(BaseView):
             sprint_id = self.request.GET.get('sprint_id')
             sprint = Sprint.query.get(sprint_id)
         project = Project.query.get(sprint.project_id)
+
+
+        sprints = [s for s in session.query(Sprint)
+                            .filter(Sprint.start<=datetime.date.today())
+                            .filter(Sprint.end>=datetime.date.today())
+        ]
+        total_worked_hours = sum([s.worked_hours for s in sprints])
+        total_anchieved_points = sum([s.achieved_points for s in sprints])
+
+        sprint.mean_velocity = sum([s.velocity for s in sprints])\
+                                 / len(sprints) if len(sprints) else 0.0
+        sprint.total_velocity = total_anchieved_points / total_worked_hours\
+                                 * 8.0 if total_worked_hours else 0.0
+
         self.v['project'] = project
         self.v['sprint'] = sprint
 
