import unittest
from datetime import datetime, timedelta

from solarconflux.events import group_consecutive_events


class EventGroupingTests(unittest.TestCase):
    def test_groups_consecutive_steps(self):
        start = datetime(2025, 1, 1)
        timeline = [
            (start, [("Earth", "Venus")]),
            (start + timedelta(hours=1), [("Venus", "Earth")]),
            (start + timedelta(hours=2), []),
        ]

        events = group_consecutive_events(timeline)

        self.assertEqual(events, [(start, start + timedelta(hours=1), ["Earth", "Venus"])])

    def test_reappearing_group_becomes_new_event(self):
        start = datetime(2025, 1, 1)
        timeline = [
            (start, [("Earth", "Venus")]),
            (start + timedelta(hours=1), []),
            (start + timedelta(hours=2), [("Earth", "Venus")]),
        ]

        events = group_consecutive_events(timeline)

        self.assertEqual(
            events,
            [
                (start, start, ["Earth", "Venus"]),
                (start + timedelta(hours=2), start + timedelta(hours=2), ["Earth", "Venus"]),
            ],
        )


if __name__ == "__main__":
    unittest.main()
