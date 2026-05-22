"""Event grouping utilities."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, List, Sequence, Tuple, TypeVar

TimeLike = TypeVar("TimeLike")
Group = Tuple[str, ...]
GroupedEvent = Tuple[TimeLike, TimeLike, List[str]]


def normalize_group(group: Iterable[str]) -> Group:
    """Return a stable tuple representation for a group of bodies."""
    return tuple(sorted(str(item) for item in group))


def group_consecutive_events(
    timeline: Sequence[Tuple[TimeLike, Iterable[Iterable[str]]]]
) -> List[GroupedEvent[TimeLike]]:
    """Group consecutive time steps with the same body group into events."""
    matching_entries: List[GroupedEvent[TimeLike]] = []
    active_groups: Dict[Group, Tuple[TimeLike, TimeLike]] = {}

    for timestamp, groups_at_step in timeline:
        normalized_groups = set()
        for group in groups_at_step:
            normalized = normalize_group(group)
            if len(normalized) > 1:
                normalized_groups.add(normalized)

        new_active_groups: Dict[Group, Tuple[TimeLike, TimeLike]] = {}
        for group in normalized_groups:
            if group in active_groups:
                start_time = active_groups[group][0]
                new_active_groups[group] = (start_time, timestamp)
            else:
                new_active_groups[group] = (timestamp, timestamp)

        for ended_group, (start_time, end_time) in active_groups.items():
            if ended_group not in new_active_groups:
                matching_entries.append((start_time, end_time, list(ended_group)))

        active_groups = new_active_groups

    for group, (start_time, end_time) in active_groups.items():
        matching_entries.append((start_time, end_time, list(group)))

    return matching_entries


def format_timestamp(value: object) -> str:
    """Format datetime-like values consistently for CSV/API output."""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if hasattr(value, "datetime"):
        return format_timestamp(value.datetime)
    if hasattr(value, "iso"):
        return str(value.iso)
    return str(value)
