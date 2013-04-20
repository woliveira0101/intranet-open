from utils import BaseTestCase
from intranet3.models import project


class SelectorMappingTest(BaseTestCase):

    def setUp(self):
        super(SelectorMappingTest, self).setUp()
        project.memcache = self.memcached_mock

    def test_memcached(self):
        t = self.mock_tracker()
        p = self.mock_project(tracker_id=t.id)
        sm = project.SelectorMapping(t)

        self.memcached_mock.set.assert_called_once_with(project.SELECTOR_CACHE_KEY % t.id, sm)
        self.memcached_mock.get.assert_called_once_with(project.SELECTOR_CACHE_KEY % t.id)

    def test_default(self):
        t = self.mock_tracker()
        p = self.mock_project(tracker_id=t.id)
        sm = project.SelectorMapping(t)

        self.assertEqual(sm.default, p.id)
        self.assertEqual(sm.by_project, {})
        self.assertEqual(sm.by_component, {})
        self.assertEqual(sm.by_version, {})

        self.assertEqual(sm.match('adasdas', 'abc', 'dsadsa'), p.id)

    def test_project(self):
        t = self.mock_tracker()
        p = self.mock_project(
            tracker_id=t.id,
            project_selector='abc'
        )
        sm = project.SelectorMapping(t)
        self.assertEqual(sm.match(None, 'abc', ''), p.id)
        self.assertEqual(sm.match(None, 'abc', 'def'), p.id)
        self.assertEqual(sm.match(None, 'abc2', ''), None)

    def test_component(self):
        t = self.mock_tracker()
        p = self.mock_project(
            tracker_id=t.id,
            project_selector='abc',
            component_selector='def',
        )

        sm = project.SelectorMapping(t)
        self.assertEqual(sm.match(None, 'abc', ''), None)
        self.assertEqual(sm.match(None, 'abc', 'def'), p.id)
        self.assertEqual(sm.match(None, 'abc2', ''), None)

    def test_version(self):
        t = self.mock_tracker()
        p = self.mock_project(
            tracker_id=t.id,
            project_selector='abc',
            version_selector='def',
        )

        sm = project.SelectorMapping(t)
        self.assertEqual(sm.match(None, 'abc', ''), None)
        self.assertEqual(sm.match(None, 'abc', 'def'), None)
        self.assertEqual(sm.match(None, 'abc2', ''), None)
        self.assertEqual(sm.match(None, 'abc', '', 'def'), p.id)

    def test_double_versions(self):
        t = self.mock_tracker()
        p1 = self.mock_project(
            tracker_id=t.id,
            project_selector='a',
            version_selector='b',
        )
        p2 = self.mock_project(
            tracker_id=t.id,
            project_selector='a',
            version_selector='c',
        )

        sm = project.SelectorMapping(t)
        self.assertEqual(sm.match(None, 'a', ''), None)
        self.assertEqual(sm.match(None, 'a', 'b'), None)
        self.assertEqual(sm.match(None, 'a', '*', 'b'), p1.id)
        self.assertEqual(sm.match(None, 'a', '*', 'c'), p2.id)
        self.assertEqual(sm.match(None, 'a', '*', 'd'), None)

    def test_double_versions2(self):
        t = self.mock_tracker()
        p1 = self.mock_project(
            tracker_id=t.id,
            project_selector='a',
            version_selector='b,c',
        )

        sm = project.SelectorMapping(t)
        self.assertEqual(sm.match(None, 'a', ''), None)
        self.assertEqual(sm.match(None, 'a', 'b'), None)
        self.assertEqual(sm.match(None, 'a', '*', 'b'), p1.id)
        self.assertEqual(sm.match(None, 'a', '*', 'c'), p1.id)
        self.assertEqual(sm.match(None, 'a', '*', 'd'), None)

    def test_component_version(self):
        t = self.mock_tracker()
        p = self.mock_project(
            tracker_id=t.id,
            project_selector='abc',
            component_selector='def',
            version_selector='ghi',
        )

        sm = project.SelectorMapping(t)
        self.assertEqual(sm.match(None, 'abc', ''), None)
        self.assertEqual(sm.match(None, 'abc', 'def'), None)
        self.assertEqual(sm.match(None, 'abc2', ''), None)
        self.assertEqual(sm.match(None, 'abc', '', 'def'), None)
        self.assertEqual(sm.match(None, 'abc', 'def', 'ghi'), p.id)

    def test_mixed(self):
        t = self.mock_tracker()
        p1 = self.mock_project(
            tracker_id=t.id,
            project_selector='a',
            component_selector='b',
            version_selector='c',
        )
        p2 = self.mock_project(
            tracker_id=t.id,
            project_selector='a',
            component_selector='d',
        )
        p3 = self.mock_project(
            tracker_id=t.id,
            project_selector='a',
            version_selector='e',
        )
        p4 = self.mock_project(
            tracker_id=t.id,
            project_selector='a',
        )
        sm = project.SelectorMapping(t)
        self.assertEqual(sm.match(None, 'a', 'b', 'c'), p1.id)
        self.assertEqual(sm.match(None, 'a', 'd', '*'), p2.id)
        self.assertEqual(sm.match(None, 'a', '*', 'e'), p3.id)
        self.assertEqual(sm.match(None, 'a', '*', '*'), p4.id)

        self.assertEqual(sm.match(None, 'a', 'd', 'e'), p2.id)

    def test_turn_off_selectors(self):
        t = self.mock_tracker()
        p = self.mock_project(
            tracker_id=t.id,
            project_selector='abc',
            component_selector='def',
            version_selector='ghi',
            turn_off_selectors=True,
        )

        sm = project.SelectorMapping(t)
        self.assertEqual(sm.match(None, 'abc', ''), None)
        self.assertEqual(sm.match(None, 'abc', 'def'), None)
        self.assertEqual(sm.match(None, 'abc2', ''), None)
        self.assertEqual(sm.match(None, 'abc', '', 'def'), None)
        self.assertEqual(sm.match(None, 'abc', 'def', 'ghi'), None)
