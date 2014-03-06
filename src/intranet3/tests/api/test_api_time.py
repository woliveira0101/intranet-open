# # coding: utf-8
# from intranet3.tests import (
#     IntranetWebTest,
#     FactoryMixin,
# )


# class ApiTimeTestCase(FactoryMixin, IntranetWebTest):

#     def test_get_method_protect(self):
#         user = self.create_user(groups=['user'])
#         # freelancer = self.create_user(is_freelancer=True,
#                                         # groups=['freelancer'])
#         client = self.create_client()
#         tracker = self.create_tracker()
#         project = self.create_project(user=user, client=client,
#                                       tracker=tracker)

#         self.login(user.name, user.email)

#         # Object Not Found
#         response = self.get(
#             '/api/times/12345678',
#             # extra_environ=self.request,
#             expect_errors=True
#         )
#         self.assertEqual(response.status_int, 404)

#         # Test Data
#         test_data = {
#             'project_id': project.id,
#             'ticket_id': 3,
#             'time': 2.5,
#             'description': "Planning meeting",
#             'timer': False,
#             'add_to_harvest': False,
#             'start_timer': False,
#         }

#         # Added as user
#         self.post_json(
#             '/api/times',
#             params=test_data,
#             # extra_environ=self.request,
#             expect_errors=True
#         )

#         # Log as freelancer
#         # self.get('/auth/logout')
#         # self.login(freelancer.name, freelancer.email)

#         # # Object Not Found
#         # response = self.get(
#         #     '/api/times/1',
#         #     extra_environ=self.request,
#         #     expect_errors=True
#         # )
#         # self.assertEqual(response.status_int, 403)

#     def test_put_method(self):
#         user = self.create_user(groups=['user'])
#         user_2 = self.create_user(groups=['user'])
#         # freelancer = self.create_user(is_freelancer=True,
#                                         # groups=['freelancer'])
#         client = self.create_client()
#         tracker = self.create_tracker()
#         project = self.create_project(user=user, client=client,
#                                       tracker=tracker)

#         self.login(user.name, user.email)

#         test_data = {
#             'project_id': project.id,
#             'ticket_id': 3,
#             'time': 2.5,
#             'description': "Planning meeting",
#             'timer': False,
#             'add_to_harvest': False,
#             'start_timer': False,
#         }

#         self.post_json(
#             '/api/times',
#             params=test_data,
#             # extra_environ=self.request,
#             expect_errors=True
#         )

#         test_data.update({
#             'time': 11.0,
#         })

#         response = self.put_json(
#             '/api/times/1',
#             params=test_data,
#             # extra_environ=self.request,
#             expect_errors=True
#         )
#         self.assertEqual(response.status_int, 200)

#         # Log as user_2
#         self.get('/auth/logout')
#         self.login(user_2.name, user_2.email)

#         # Another user can not change data
#         response = self.put_json(
#             '/api/times/1',
#             params=test_data,
#             # extra_environ=self.request,
#             expect_errors=True
#         )
#         self.assertEqual(response.status_int, 400)

#     def test_delete_method(self):
#         user = self.create_user(groups=['user'])
#         user_2 = self.create_user(groups=['user'])
#         # freelancer = self.create_user(is_freelancer=True,
#                                         # groups=['freelancer'])
#         client = self.create_client()
#         tracker = self.create_tracker()
#         project = self.create_project(user=user, client=client,
#                                       tracker=tracker)

#         self.login(user.name, user.email)

#         test_data = {
#             'project_id': project.id,
#             'ticket_id': 3,
#             'time': 2.5,
#             'description': "Planning meeting",
#             'timer': False,
#             'add_to_harvest': False,
#             'start_timer': False,
#         }

#         self.post_json(
#             '/api/times',
#             params=test_data,
#             # extra_environ=self.request,
#             expect_errors=True
#         )

#         # Log as user_2
#         self.get('/auth/logout')
#         self.login(user_2.name, user_2.email)

#         # Try delete
#         response = self.delete(
#             '/api/times/1',
#             # extra_environ=self.request,
#             expect_errors=True
#         )
#         self.assertEqual(response.status_int, 400)

#         # Back to user
#         self.get('/auth/logout')
#         self.login(user.name, user.email)
#         response = self.delete(
#             '/api/times/1',
#             # extra_environ=self.request,
#         )
#         self.assertEqual(response.status_int, 200)

#     def test_get_response(self):
#         user = self.create_user(groups=['user'])
#         # user_2 = self.create_user(groups=['user'])
#         # freelancer = self.create_user(is_freelancer=True,
#                                         # groups=['freelancer'])
#         client = self.create_client()
#         tracker = self.create_tracker()
#         project = self.create_project(user=user, client=client,
#                                       tracker=tracker)

#         self.login(user.name, user.email)

#         test_data = {
#             'project_id': project.id,
#             'ticket_id': 3,
#             'time': 2.5,
#             'description': "Planning meeting",
#             'timer': False,
#             'add_to_harvest': False,
#             'start_timer': False,
#         }

#         self.post_json(
#             '/api/times',
#             params=test_data,
#             # extra_environ=self.request,
#             expect_errors=True
#         )

#         response = self.get(
#             "/api/times/1",
#             # extra_environ=self.request,
#             expect_errors=True,
#         )

#         self.assertEqual(response.status_int, 200)

#         data = response.json

#         self.assertIsInstance(data, dict)
#         self.assertEqual(data['project']['client_name'], client.name)
#         self.assertEqual(data['project']['project_name'], project.name)
#         self.assertEqual(data['ticket_id'], 3)
#         self.assertEqual(data['time'], 2.5)
#         self.assertEqual(data['tracker_url'],
#                          "%s/show_bug.cgi?id=%s" % (tracker.url, 3))
#         self.assertEqual(data['desc'], "Planning meeting")
