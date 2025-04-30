from solarconflux.spatialitems.functions import get_trajectories, matching_dates, save_match, save_plot, get_info
import os

def SolarConflux():
    print("\nAvailable bodies for trajectory retrieval:")
    get_info()

    body_list = input("\nEnter the list of bodies to analyze (comma-separated and no space, e.g., BepiColombo,Solar Orbiter,Earth): ").split(',')

    start_time = input("\nEnter the start time (e.g., 2025-01-01): ")
    end_time = input("Enter the end time (e.g., 2025-12-31): ")

    step_choice = input("\nDo you want to choose the time step? y for yes, n for no (default: 60 min): ")
    if step_choice.lower() == 'y':
        step = input("Enter the time step (e.g., 60m): ")
    else:
        step = '60m'

    print("\nAvailable geometric alignments: opposition, cone, quadrature, arbitrary, parker")
    geometry_choice = [g.strip().lower() for g in input("Enter alignment types (comma-separated): ").split(',')]

    arbitrary_angle = float(input("Enter the desired angle in degrees: ")) if 'arbitrary' in geometry_choice else None
    
    speed_choice = input("\nDo you want to choose the solar wind speed? y for yes, n for no (default: 400 km/s): ")
    if speed_choice.lower() == 'y':
        u_sw = float(input("Enter solar wind speed for Parker spiral (km/s): ")) * 1e3  # convert to m/s
    else:
        u_sw = 400e3  # default in m/s

    base_path = input("\nEnter the folder path where results should be saved (e.g., /Users/xxx/output): ").strip()
    if not os.path.exists(base_path):
        os.makedirs(base_path)
        print(f"Created directory: {base_path}")

    print("\nFetching trajectories...")
    trajectories = get_trajectories(body_list, start_time, end_time, step)

    print("\nLooking for matching dates...")
    match = matching_dates(geometry_choice, body_list, trajectories, arbitrary_angle=arbitrary_angle, u_sw=u_sw)

    print("\nSaving the results...")
    save_match(match, base_path)
    save_plot(match, trajectories, base_path)

if __name__ == "__main__":
    SolarConflux()