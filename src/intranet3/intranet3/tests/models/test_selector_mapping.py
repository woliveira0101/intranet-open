from intranet3 import models
from intranet3.testing import (
    IntranetTest,
    FactoryMixin,
)


class SelectorMappingTest(FactoryMixin, IntranetTest):

    def setUp(self):
        super(SelectorMappingTest, self).setUp()

    def prepare_selector_mapping(self, tracker=None, **kwargs):
        if tracker is None:
            tracker = self.create_tracker()
        project = self.create_project(
            tracker=tracker,
            **kwargs
        )
        sm = models.project.SelectorMapping(tracker)
        return sm, project

    def test_default(self):
        sm, p = self.prepare_selector_mapping()

        self.assertEqual(sm.default, p.id)
        self.assertEqual(sm.by_project, {})
        self.assertEqual(sm.by_component, {})
        self.assertEqual(sm.by_version, {})

        self.assertEqual(sm.match('adasdas', 'abc', 'dsadsa'), p.id)

    def test_project(self):
        sm, p = self.prepare_selector_mapping(project_selector='abc')
        self.assertEqual(sm.match(None, 'abc', ''), p.id)
        self.assertEqual(sm.match(None, 'abc', 'def'), p.id)
        self.assertEqual(sm.match(None, 'abc2', ''), None)

    def test_component(self):
        sm, p = self.prepare_selector_mapping(
            project_selector='abc',
            component_selector='def',
        )

        self.assertEqual(sm.match(None, 'abc', ''), None)
        self.assertEqual(sm.match(None, 'abc', 'def'), p.id)
        self.assertEqual(sm.match(None, 'abc2', ''), None)

    def test_version(self):
        sm, p = self.prepare_selector_mapping(
            project_selector='abc',
            version_selector='def',
        )

        self.assertEqual(sm.match(None, 'abc', ''), None)
        self.assertEqual(sm.match(None, 'abc', 'def'), None)
        self.assertEqual(sm.match(None, 'abc2', ''), None)
        self.assertEqual(sm.match(None, 'abc', '', 'def'), p.id)

    def test_double_versions(self):
        tracker = self.create_tracker()
        p1 = self.create_project(
            tracker=tracker,
            project_selector='a',
            version_selector='b',
        )
        p2 = self.create_project(
            tracker=tracker,
            project_selector='a',
            version_selector='c',
        )
        sm = models.project.SelectorMapping(tracker)

        self.assertEqual(sm.match(None, 'a', ''), None)
        self.assertEqual(sm.match(None, 'a', 'b'), None)
        self.assertEqual(sm.match(None, 'a', '*', 'b'), p1.id)
        self.assertEqual(sm.match(None, 'a', '*', 'c'), p2.id)
        self.assertEqual(sm.match(None, 'a', '*', 'd'), None)

    def test_double_versions2(self):
        sm, p = self.prepare_selector_mapping(
            project_selector='a',
            version_selector='b,c',
        )

        self.assertEqual(sm.match(None, 'a', ''), None)
        self.assertEqual(sm.match(None, 'a', 'b'), None)
        self.assertEqual(sm.match(None, 'a', '*', 'b'), p.id)
        self.assertEqual(sm.match(None, 'a', '*', 'c'), p.id)
        self.assertEqual(sm.match(None, 'a', '*', 'd'), None)

    def test_component_version(self):
        sm, p = self.prepare_selector_mapping(
            project_selector='abc',
            component_selector='def',
            version_selector='ghi',
        )

        self.assertEqual(sm.match(None, 'abc', ''), None)
        self.assertEqual(sm.match(None, 'abc', 'def'), None)
        self.assertEqual(sm.match(None, 'abc2', ''), None)
        self.assertEqual(sm.match(None, 'abc', '', 'def'), None)
        self.assertEqual(sm.match(None, 'abc', 'def', 'ghi'), p.id)

    def test_mixed(self):
        tracker = self.create_tracker()
        p1 = self.create_project(
            tracker=tracker,
            project_selector='a',
            component_selector='b',
            version_selector='c',
        )
        p2 = self.create_project(
            tracker=tracker,
            project_selector='a',
            component_selector='d',
        )
        p3 = self.create_project(
            tracker=tracker,
            project_selector='a',
            version_selector='e',
        )
        p4 = self.create_project(
            tracker=tracker,
            project_selector='a',
        )
        sm = models.project.SelectorMapping(tracker)

        self.assertEqual(sm.match(None, 'a', 'b', 'c'), p1.id)
        self.assertEqual(sm.match(None, 'a', 'd', '*'), p2.id)
        self.assertEqual(sm.match(None, 'a', '*', 'e'), p3.id)
        self.assertEqual(sm.match(None, 'a', '*', '*'), p4.id)
        self.assertEqual(sm.match(None, 'a', 'd', 'e'), p2.id)

    def test_turn_off_selectors(self):
        sm, p = self.prepare_selector_mapping(
            project_selector='abc',
            component_selector='def',
            version_selector='ghi',
            turn_off_selectors=True,
        )

        self.assertEqual(sm.match(None, 'abc', ''), None)
        self.assertEqual(sm.match(None, 'abc', 'def'), None)
        self.assertEqual(sm.match(None, 'abc2', ''), None)
        self.assertEqual(sm.match(None, 'abc', '', 'def'), None)
        self.assertEqual(sm.match(None, 'abc', 'def', 'ghi'), None)
