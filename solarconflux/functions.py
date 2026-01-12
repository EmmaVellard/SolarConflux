"""
This script retrieves and analyzes the trajectories of multiple spacecraft and planets using the SolarConflux module.
It checks for specific geometric alignments (Opposition, Cone, Quadrature, Parker, etc.) between these objects
in the heliocentric reference frame.

Main Features:
1. Retrieve the trajectories of spacecraft and planets from the Horizons database.
2. Transform coordinates into the Heliocentric Inertial (HCI) reference frame.
3. Detect geometric alignments between multiple celestial bodies.
4. Save the results in CSV files for further analysis.
5. Generate polar coordinate plots of spacecraft positions over specific periods.

Modules Used:
- Astropy / SunPy: Handling coordinates and retrieving Horizons data.
- Matplotlib: Generating trajectory plots.
- CSV / OS: Managing the export of results as files.

Inputs:
- List of spacecraft and planets to analyze.
- Date range for analysis.
- Type of alignments to detect (e.g., Parker Spiral).

Outputs:
- A CSV file containing the detected alignment dates.
- Graphical representations of trajectories in polar coordinates.

Author: Emma Vellard
Date: 2025
"""

from solarconflux.geometries import Geometry

import os
import csv
import math

import numpy as np
import matplotlib.pyplot as plt

import astropy.units as u
from astropy.time import Time
from sunpy.coordinates import get_horizons_coord, HeliocentricInertial

def get_infos():
    """
    Returns the mapping of celestial bodies and spacecraft to their respective Horizons identifiers,
    along with their available data time ranges, given by https://sscweb.gsfc.nasa.gov/scansat.shtml 
    """
    return {
        'BepiColombo': {'id': 'BepiColombo', 'start': '2018-10-20 02:13', 'end': '2027-03-13 22:59'},
        'Solar Orbiter': {'id': 'Solar Orbiter', 'start': '2020-02-10 04:56', 'end': '2030-11-20 05:14'},
        'PSP': {'id': 'Parker Solar Probe', 'start': '2018-08-12 08:30', 'end': '2024-10-16 17:58'},
        'Stereo-A': {'id': 'Stereo-A', 'start': '2010-01-01 00:00', 'end': '2024-12-26 23:48'},
        'Juice': {'id': 'Juice', 'start': '2023-04-14 12:43', 'end': '2031-07-21 06:02'},
        'Maven': {'id': 'Maven', 'start': '2013-11-21 20:01', 'end': '2024-09-30 23:58'},
        'Juno': {'id': 'Juno', 'start': '2013-08-01 01:01', 'end': '2020-02-15 00:00'},
        'SDO': {'id': 'SDO', 'start': '2010-05-22 00:00', 'end': '2025-01-26 04:52'},
        'SOHO': {'id': 'SOHO', 'start': '1995-12-02 00:12', 'end': '2018-02-04 23:36'},
        'ACE': {'id': -92, 'start': '1997-08-25 00:00', 'end': '2025-01-26 04:52'},
        'Venus': {'id': 299, 'start': '1971-01-01 00:00', 'end': '2040-12-31 23:58'},
        'Earth': {'id': 399, 'start': 'NA', 'end': 'NA'},
        'Mars': {'id': 499, 'start': '1971-01-01 01:00', 'end': '2040-12-31 23:58'},
        'Jupiter': {'id': 599, 'start': '1971-01-01 00:00', 'end': '2040-12-31 23:58'},
        'Sun': {'id': 'Sun', 'start': 'NA', 'end': 'NA'},
    }

def get_info():
    """
    Prints the list of available bodies that can be used in get_trajectories.
    """
    body_info = get_infos()

    print("Spacecraft: (yyyy-mm-dd hh:mm)\n")
    for body, info in body_info.items():
        print(f"- {body}: {info['start']} to {info['end']}")
    
    print("\nFor more information, refer to the Horizons documentation.")

def get_trajectories(body_list, start_time, end_time, step='60m'):
    """
    Fetch and convert trajectories to Heliocentric Inertial frame for a list of spacecraft or celestial bodies.

    Parameters:
    - body_list: List of bodies as strings (e.g., ['BepiColombo', 'Venus', 'Earth'])
    - start_time: Start time as a string or datetime (will be parsed with parse_time)
    - end_time: End time as a string or datetime (will be parsed with parse_time)
    - step: Time step for trajectory data retrieval (default is "60m" for 60 minutes)

    Returns:
    - A dictionary where keys are body names and values are their transformed trajectory data.
    """
    body_info = get_infos()
    trajectories = {}

    for body in body_list:
        if body in body_info:
            body_id = body_info[body]['id']
            coord = get_horizons_coord(body_id, {'start': start_time, 'stop': end_time, 'step': step})
            trajectories[body] = coord.transform_to(HeliocentricInertial())
        else:
            print(f"!! Warning: '{body}' is not recognized and will be skipped.")

    return trajectories

def matching_dates(geometry_choices, spacecraft_names, trajectories, frame=HeliocentricInertial, cone_width=np.radians(10), tolerance=np.radians(10), arbitrary_angle=None, u_sw=400e3):
    """
    Check for multiple geometries in a list of choices and find matching entries for each.
    """
    all_matching_entries = {}
    geometry = Geometry(spacecraft_names, trajectories, frame, cone_width, tolerance)

    for mode in geometry_choices:
        if mode in ['opposition', 'cone', 'quadrature', 'arbitrary', 'parker', 'coneparker']:
            matches = geometry.check_geometry(mode=mode.lower(), arbitrary_angle=arbitrary_angle, u_sw=u_sw)
            if matches:
                all_matching_entries[mode] = matches
                print(f"{mode}: {len(matches)} matches found.")
            else:
                print(f"{mode}: no matches.")

    return all_matching_entries

def save_match(matching_entries, save_base_path):
    """
    Save matching entries for multiple geometries to a single CSV file.
    """
    os.makedirs(save_base_path, exist_ok=True)

    combined = [(start, end, geom, group) for geom, entries in matching_entries.items() for start, end, group in entries]
    sorted_combined = sorted(combined, key=lambda x: x[0])

    if sorted_combined:
        folder = f"{sorted_combined[0][0][:10]}_to_{sorted_combined[-1][1][:10]}"
        path = os.path.join(save_base_path, folder)
        os.makedirs(path, exist_ok=True)

        with open(os.path.join(path, f"{folder}.csv"), mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["start_date", "end_date", "geometry", "spacecrafts"])
            for entry in sorted_combined:
                writer.writerow(entry)

        print("Matching entries saved.")
    else:
        print("No entries to save.")

def coord_to_polar(coord):
    """Convert SkyCoord object to polar coordinates (longitude, distance)."""
    return coord.spherical.lon.rad, coord.spherical.distance.value

def save_plot(matching_trajectories, trajectories, save_base_path):
    """
    Save plots of spacecraft positions over time based on matching geometries.
    """
    colors = ['blue', 'red', 'purple', 'cyan', 'green', 'brown', 'limegreen', 'yellow','grey', 'pink']
    plots_per_file = 15

    all_dates = [(entry[0], entry[1]) for entries in matching_trajectories.values() for entry in entries]
    if not all_dates:
        print("No plots to save.")
        return

    folder = f"{min(all_dates)[0][:10]}_to_{max(all_dates)[1][:10]}"
    main_path = os.path.join(save_base_path, folder)
    os.makedirs(main_path, exist_ok=True)

    for geom, matches in matching_trajectories.items():
        geom_path = os.path.join(main_path, geom)
        os.makedirs(geom_path, exist_ok=True)

        for file_idx, chunk_start in enumerate(range(0, len(matches), plots_per_file)):
            chunk = matches[chunk_start:chunk_start + plots_per_file]
            rows = math.ceil(len(chunk) / 3)
            fig, axes = plt.subplots(rows, 3, subplot_kw={'projection': 'polar'}, figsize=(15, 5 * rows))
            axes = axes.flatten()

            for idx, (start, end, group) in enumerate(chunk):
                ax = axes[idx]
                ax.plot(0, 0, 'o', label='Sun', color='orange', markersize=5)
                plotted = {}
                for sc in group:
                    coords = trajectories.get(sc, [])
                    color = colors[list(trajectories.keys()).index(sc) % len(colors)]
                    for coord in coords:
                        if start <= coord.obstime.iso <= end:
                            ax.scatter(*coord_to_polar(coord), color=color, s=3, label=sc if sc not in plotted else "")
                            plotted[sc] = True
                ax.set_title(f"{geom} {start[:10]} to {end[:10]}")
                ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.3), ncol=2)

            plt.tight_layout(h_pad=2)
            plt.savefig(os.path.join(geom_path, f"{chunk[0][0][:10]}_to_{chunk[-1][1][:10]}.png"))
            plt.close(fig)

        print("Matching entries saved.")