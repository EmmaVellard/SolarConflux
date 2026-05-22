"""Supported body metadata and validation helpers."""

from __future__ import annotations

from copy import deepcopy
from typing import Dict, Iterable, List, Mapping, MutableMapping, Union

BodyInfo = Dict[str, Union[str, int]]

_BODY_INFO: Dict[str, BodyInfo] = {
    "BepiColombo": {
        "id": "BepiColombo",
        "start": "2018-10-20 02:13",
        "end": "2027-03-13 22:59",
    },
    "Solar Orbiter": {
        "id": "Solar Orbiter",
        "start": "2020-02-10 04:56",
        "end": "2030-11-20 05:14",
    },
    "PSP": {
        "id": "Parker Solar Probe",
        "start": "2018-08-12 08:30",
        "end": "2024-10-16 17:58",
    },
    "Stereo-A": {
        "id": "Stereo-A",
        "start": "2010-01-01 00:00",
        "end": "2024-12-26 23:48",
    },
    "Juice": {
        "id": "Juice",
        "start": "2023-04-14 12:43",
        "end": "2031-07-21 06:02",
    },
    "Maven": {
        "id": "Maven",
        "start": "2013-11-21 20:01",
        "end": "2024-09-30 23:58",
    },
    "Messenger": {
        "id": "Messenger",
        "start": "2004-08-03 07:14",
        "end": "2015-04-30 19:23",
    },
    "Juno": {
        "id": "Juno",
        "start": "2013-08-01 01:01",
        "end": "2020-02-15 00:00",
    },
    "SDO": {
        "id": "SDO",
        "start": "2010-05-22 00:00",
        "end": "2025-01-26 04:52",
    },
    "SOHO": {
        "id": "SOHO",
        "start": "1995-12-02 00:12",
        "end": "2018-02-04 23:36",
    },
    "ACE": {"id": -92, "start": "1997-08-25 00:00", "end": "2025-01-26 04:52"},
    "Venus": {"id": 299, "start": "1971-01-01 00:00", "end": "2040-12-31 23:58"},
    "Earth": {"id": 399, "start": "NA", "end": "NA"},
    "Mars": {"id": 499, "start": "1971-01-01 01:00", "end": "2040-12-31 23:58"},
    "Jupiter": {"id": 599, "start": "1971-01-01 00:00", "end": "2040-12-31 23:58"},
    "Sun": {"id": "Sun", "start": "NA", "end": "NA"},
}


def get_infos() -> Dict[str, BodyInfo]:
    """Return supported bodies and their Horizons identifiers/date ranges."""
    return deepcopy(_BODY_INFO)


def supported_body_names() -> List[str]:
    """Return supported body names in display order."""
    return list(_BODY_INFO)


def normalize_body_list(bodies: Union[str, Iterable[str]]) -> List[str]:
    """Normalize comma-separated or iterable body input into unique names."""
    if isinstance(bodies, str):
        raw_bodies = bodies.split(",")
    else:
        raw_bodies = list(bodies)

    normalized: List[str] = []
    seen = set()
    for body in raw_bodies:
        name = str(body).strip()
        if not name:
            continue
        if name not in seen:
            normalized.append(name)
            seen.add(name)

    if not normalized:
        raise ValueError("At least one body must be provided.")
    return normalized


def validate_body_names(bodies: Union[str, Iterable[str]]) -> List[str]:
    """Validate body names and return normalized values."""
    normalized = normalize_body_list(bodies)
    unknown = [body for body in normalized if body not in _BODY_INFO]
    if unknown:
        supported = ", ".join(supported_body_names())
        raise ValueError(
            "Unsupported body name(s): "
            + ", ".join(unknown)
            + f". Supported bodies are: {supported}."
        )
    return normalized


def horizons_ids_for_bodies(bodies: Iterable[str]) -> MutableMapping[str, Union[str, int]]:
    """Return Horizons identifiers for validated body names."""
    body_info: Mapping[str, BodyInfo] = _BODY_INFO
    return {body: body_info[body]["id"] for body in bodies}
