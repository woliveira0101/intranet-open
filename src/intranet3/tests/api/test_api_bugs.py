# coding: utf-8

from intranet3.tests import (
    IntranetWebTest,
    FactoryMixin,
)


# class ApiBugTestCase(FactoryMixin, IntranetWebTest):

#     def test_api_bug_view_not_logged(self):
#         response = self.get('/api/bugs')
#         self.assertEqual(response.status_code, 302)

#         response = response.follow()
#         self.assertEqual(response.request.path, "/auth/logout_view")

#     def test_response(self):
#         user = self.create_user(groups=['user'])

#         self.login(user.name, user.email)

#         response = self.get('/api/bugs')
#         self.assertEqual(response.status_int, 200)
#         self.assertNotEqual(response.json.get('bugs'), None)

#         self.assertIsInstance(response.json.get('bugs'), list)

#     def test_permissions(self):
#         user = self.create_user(groups=['user'])
#         _user = self.create_user()

#         self.login(user.name, user.email)

#         response = self.get('/api/bugs')
#         self.assertEqual(response.status_int, 200)

#         # Log user without persmclea
#         self.app.get('/auth/logout')
#         self.login(_user.name, _user.email)

#         response = self.get('/api/bugs',
#                                 expect_errors=True)
#         self.assertEqual(response.status_int, 403)
