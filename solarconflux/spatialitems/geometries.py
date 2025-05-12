"""
This module defines the `Geometry` class, which analyzes the spatial relationships between spacecraft  
and celestial bodies using their trajectories. It checks for specific geometric alignments such as:  

1. Opposition: Spacecraft are positioned on opposite sides of the Sun (180° apart).  
2. Cone: Spacecraft are within a defined angular separation.  
3. Quadrature: Spacecraft are at right angles (90° apart).  
4. Arbitrary Angle: Spacecraft align at a user-defined angular separation.  
5. Parker Spiral: Spacecraft follow the same Parker spiral trajectory considering solar wind speed.  
6. Cone Parker: Spacecraft are within a cone and follow the same Parker spiral trajectory.

Features:
- Computes spacecraft longitudes from their trajectories.
- Determines Parker spiral longitudes using a given solar wind speed.
- Identifies time periods when spacecraft match selected alignment criteria.
- Groups spacecraft based on geometric conditions and tracks their active alignment periods.
- Outputs a list of time periods when the alignment conditions are met.

Inputs:
- Spacecraft trajectories in SkyCoord format.
- Geometric mode selection (e.g., opposition, quadrature, Parker spiral).
- Tolerance levels for angular comparisons.
- Solar wind speed (for Parker spiral calculations).

Outputs:
- A list of tuples containing start and end times for each alignment, along with the participating spacecraft.

Author: Emma Vellard
Date: 2025  
"""

import numpy as np
from sunpy.coordinates import HeliocentricInertial
from astropy.coordinates import SkyCoord
from astropy.time import Time
from astropy import units as u


class Geometry:
    def __init__(self, spacecraft_names, trajectories, frame=HeliocentricInertial,
                cone_width=np.radians(10), tolerance=np.radians(10), solar_rotation_period=25.38):
        self.spacecraft_names = spacecraft_names
        self.trajectories = trajectories
        self.frame = frame
        self.cone_width = cone_width
        self.tolerance = tolerance
        self.angles, self.latitudes = self.calculate_angles()

        self.tolerance_parker = np.radians(5)  # radians
        self.source_surface_radius = 2.5 * 696000.0  # km (2.5 Rsun)
        self.solar_rotation_rate = 2 * np.pi / (solar_rotation_period * 24 * 3600)  # rad/s

    def calculate_angles(self):
        angles = []
        latitudes = []
        for step in range(len(next(iter(self.trajectories.values())))):
            step_angles = []
            step_lats = []
            for skycoords in self.trajectories.values():
                coord = skycoords[step].spherical
                lon = coord.lon.to_value(u.rad) % (2 * np.pi)
                lat = coord.lat.to_value(u.rad)
                step_angles.append(lon)
                step_lats.append(lat)
            angles.append(step_angles)
            latitudes.append(step_lats)
        return angles, latitudes

    def parker_spiral_function(self, r_km, lon_rad, u_sw_mps):
        """
        r_km: distance from Sun in kilometers
        lon_rad: heliocentric longitude in radians
        u_sw_mps: solar wind speed in meters per second
        """
        r_m = r_km * 1e3  # Convert to meters
        r_ss_m = self.source_surface_radius * 1e3  # Source surface radius in meters
        phi_0 = lon_rad + (self.solar_rotation_rate / u_sw_mps) * (r_m - r_ss_m)
        return phi_0 % (2 * np.pi)

    def check_geometry(self, mode='opposition', arbitrary_angle=None, u_sw=400e3):
        matching_entries = []
        num_steps = len(next(iter(self.trajectories.values())))
        active_groups = {}

        for step in range(num_steps):
            date = next(iter(self.trajectories.values()))[step].transform_to(self.frame).obstime.datetime
            groups = []

            for spacecraft1, skycoords1 in self.trajectories.items():
                lon1 = self.angles[step][list(self.trajectories).index(spacecraft1)]
                lat1 = self.latitudes[step][list(self.trajectories).index(spacecraft1)]
                r1 = skycoords1[step].spherical.distance.to('km').value

                group = {spacecraft1}

                for spacecraft2, skycoords2 in self.trajectories.items():
                    if spacecraft1 == spacecraft2:
                        continue

                    lon2 = self.angles[step][list(self.trajectories).index(spacecraft2)]
                    lat2 = self.latitudes[step][list(self.trajectories).index(spacecraft2)]
                    r2 = skycoords2[step].spherical.distance.to('km').value

                    if mode == 'opposition':
                        # no constraint on latitude
                        condition = np.isclose(np.abs(lon1 - lon2), np.pi, atol=self.tolerance)
                    elif mode == 'cone':
                        # no constraint on latitude
                        condition = np.abs(lon1 - lon2) <= self.cone_width
                    elif mode == 'quadrature':
                        condition = (np.isclose(np.abs(lon1 - lon2), np.pi / 2, atol=self.tolerance)) or (np.isclose(np.abs(lat1 - lat2), np.pi / 2, atol=self.tolerance))
                    elif mode == 'arbitrary' and arbitrary_angle is not None:
                        condition = np.isclose(np.abs(lon1 - lon2), arbitrary_angle, atol=self.tolerance)
                    elif mode == 'parker':
                        phi0_1 = self.parker_spiral_function(r1, lon1, u_sw)
                        phi0_2 = self.parker_spiral_function(r2, lon2, u_sw)
                        condition = (np.isclose(phi0_1, phi0_2, atol=self.tolerance_parker)) and (np.isclose(lat1, lat2, atol=self.tolerance))
                    elif mode == 'coneparker':
                        phi0_1 = self.parker_spiral_function(r1, lon1, u_sw)
                        phi0_2 = self.parker_spiral_function(r2, lon2, u_sw)
                        condition = (np.abs(lon1 - lon2) <= self.cone_width) and (np.isclose(phi0_1, phi0_2, atol=self.tolerance_parker)) and (np.isclose(lat1, lat2, atol=self.tolerance))
                    else:
                        condition = False

                    if condition:
                        group.add(spacecraft2)

                if len(group) > 1 and not (len(group) == 2 and 'Sun' in group):
                    groups.append(tuple(sorted(group)))

            new_active_groups = {}
            for group in groups:
                if group in active_groups:
                    start_date = active_groups[group][0]
                    new_active_groups[group] = (start_date, date)
                else:
                    new_active_groups[group] = (date, date)

            for ended_group, (start_date, end_date) in active_groups.items():
                if ended_group not in new_active_groups:
                    matching_entries.append((
                        start_date.strftime('%Y-%m-%d %H:%M:%S'),
                        end_date.strftime('%Y-%m-%d %H:%M:%S'),
                        list(ended_group)
                    ))

            active_groups = new_active_groups

        for group, (start_date, end_date) in active_groups.items():
            matching_entries.append((
                start_date.strftime('%Y-%m-%d %H:%M:%S'),
                end_date.strftime('%Y-%m-%d %H:%M:%S'),
                list(group)
            ))

        return matching_entries