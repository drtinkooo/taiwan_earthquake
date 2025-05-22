# This script performs flood extent mapping using Sentinel-1 SAR data in Google Earth Engine.
# It identifies water bodies before and after a specified flood event period to map the flood extent.
# Key steps include:
# 1. Setting up Earth Engine API (requires user authentication and project ID).
# 2. Defining an Area of Interest (AOI) and time periods for analysis.
# 3. Loading and preprocessing Sentinel-1 GRD data (filtering, speckle correction).
# 4. Identifying water areas based on a backscatter threshold.
# 5. Calculating the flood extent by comparing water masks from before and after the event.
# 6. Providing commented-out examples for visualizing the results with 'geemap' and
#    exporting the flood map to Google Drive or as an Earth Engine Asset.

import ee

# --- User Configuration: Earth Engine Setup ---
# 1. Authenticate to Earth Engine:
#    - Uncomment the line `ee.Authenticate()` below.
#    - Run the script in a terminal or command prompt.
#    - You will be prompted to log in to your Google account and grant access to Earth Engine.
# ee.Authenticate()

# 2. Initialize the Earth Engine API:
#    - Uncomment the line `ee.Initialize(...)` below.
#    - IMPORTANT: Replace 'YOUR_PROJECT_ID_HERE' with your actual Google Cloud Project ID
#      that is enabled for Earth Engine use.
# ee.Initialize(project='YOUR_PROJECT_ID_HERE')

print("Earth Engine API setup section complete. Please ensure you have uncommented and correctly configured authentication/initialization if you intend to run GEE operations.")

# --- User Configuration: Analysis Parameters ---
# 1. Define the Area of Interest (AOI)
#    - Coordinates are [min_longitude, min_latitude, max_longitude, max_latitude].
#    - Example is for Naypyidaw, Myanmar. Modify these for your region.
aoi = ee.Geometry.Rectangle([95.9, 19.6, 96.3, 19.9]) # Longitude/Latitude for Naypyidaw

# 2. Define Time Periods for Before and After the Flood Event
#    - Format is 'YYYY-MM-DD'.
#    - Change these placeholder dates to match the specific flood event you are analyzing.
before_start_date = '2023-06-01'
before_end_date = '2023-06-30'
after_start_date = '2023-07-15' # Should be after before_end_date
after_end_date = '2023-07-30'

# 3. Define Sentinel-1 Orbit Pass
#    - Options: 'ASCENDING', 'DESCENDING'.
#    - Using a single pass helps with consistency, but consider data availability.
#    - If data is sparse, you might need to process both or choose the one with better coverage.
selected_orbit_pass = 'ASCENDING'

# 4. Define Water Threshold for Sentinel-1 VV Polarization
#    - This value (in dB) is a common starting point for identifying water bodies.
#    - Water typically has low backscatter values (more negative).
#    - IMPORTANT: This threshold may need significant adjustment based on local conditions,
#      vegetation, sensor calibration, and specific flood characteristics.
#      Experimentation is often required.
water_threshold_vv = -18  # Units: dB

print("User-defined AOI, time periods, orbit pass, and water threshold have been set.")

# --- Sentinel-1 Data Processing Function ---
def get_sentinel1_processed(aoi_geom, start_date_str, end_date_str, orbit_pass_str='ASCENDING'):
    """
    Loads, filters, and preprocesses Sentinel-1 GRD data for a given AOI and time range.
    Steps:
    1. Load Sentinel-1 GRD ImageCollection.
    2. Filter by AOI and date range.
    3. Filter for IW (Interferometric Wide swath) instrument mode.
    4. Filter for VV polarization (most common for water mapping).
    5. Filter by specified orbit pass (ASCENDING or DESCENDING).
    6. Apply a speckle filter (focal median) to reduce noise.
    7. Create a median composite from all selected images.
    8. Clip the composite to the AOI.
    Returns an ee.Image object.
    """
    print(f"Processing Sentinel-1 for period: {start_date_str} to {end_date_str}, Orbit: {orbit_pass_str}")

    s1_collection = ee.ImageCollection('COPERNICUS/S1_GRD') \
        .filterBounds(aoi_geom) \
        .filterDate(ee.Date(start_date_str), ee.Date(end_date_str)) \
        .filter(ee.Filter.eq('instrumentMode', 'IW')) \
        .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV')) \
        .filter(ee.Filter.eq('orbitProperties_pass', orbit_pass_str)) \
        .select(['VV']) # Select only the VV band after filtering

    # Apply speckle filter to each image in the collection
    def speckle_filter(image):
        # focal_median is a common speckle filter. Radius is in meters.
        return image.focal_median(radius=50, units='meters').copyProperties(image, ['system:time_start'])

    s1_collection_filtered = s1_collection.map(speckle_filter)

    # Create a median composite from the filtered images
    s1_composite = s1_collection_filtered.median()

    # Clip the composite to the precise AOI geometry
    s1_composite_clipped = s1_composite.clip(aoi_geom)

    return s1_composite_clipped

# --- Process Data for Before and After Periods ---
# Call the function for the 'before' period
s1_before = get_sentinel1_processed(aoi, before_start_date, before_end_date, selected_orbit_pass)
print(f"Processing Sentinel-1 data for 'before' period ({before_start_date} to {before_end_date}) complete.")

# Call the function for the 'after' period
s1_after = get_sentinel1_processed(aoi, after_start_date, after_end_date, selected_orbit_pass)
print(f"Processing Sentinel-1 data for 'after' period ({after_start_date} to {after_end_date}) complete.")

# --- Identify Water Areas ---
# Apply the defined threshold to create binary water masks.
# Pixels with VV backscatter values less than the threshold are considered water (value 1).

# Identify water areas in the 'before' image
water_mask_before = s1_before.lt(water_threshold_vv) # Less than threshold means water
water_mask_before = water_mask_before.rename('water_before') # Rename band for clarity
print(f"Water mask for 'before' period identified using threshold: {water_threshold_vv} dB.")

# Identify water areas in the 'after' image
water_mask_after = s1_after.lt(water_threshold_vv)
water_mask_after = water_mask_after.rename('water_after')
print(f"Water mask for 'after' period identified using threshold: {water_threshold_vv} dB.")

# --- Calculate Flood Extent ---
# Flood extent is defined as areas that were NOT water in the 'before' image
# AND ARE water in the 'after' image.
# Update: selfMask() is used to make 0s (non-water or non-flood) transparent for better visualization.
flood_extent_map = water_mask_after.And(water_mask_before.Not())
flood_extent_map = flood_extent_map.rename('flood_extent').selfMask() # selfMask for visualization
print("Flood extent calculated (areas that were not water before but are water after). Masked non-flood areas.")

# --- Visualization and Export (Commented Out Examples) ---
# The following sections provide examples for visualizing the `flood_extent_map`
# using the 'geemap' library in a Jupyter environment (e.g., Google Colab)
# and for exporting the map to Google Drive or as an Earth Engine Asset.
#
# IMPORTANT:
# - Ensure Earth Engine is initialized (ee.Authenticate() and ee.Initialize() at the top of the script).
# - For geemap, install it: `pip install geemap` in your Python environment.
# - For exports, tasks run on Google's servers and can take time. Monitor them in the
#   GEE Code Editor's "Tasks" tab or programmatically.

# --- Visualization Example with geemap (for Jupyter environments) ---
# """
# import geemap # Import geemap if you plan to use it

# try:
#     # Attempt to create a map centered on the AOI
#     Map = geemap.Map()
#     Map.centerObject(aoi, 10) # Adjust zoom level (e.g., 10-12) as needed

#     # Visualization parameters for the flood extent (e.g., blue for flood)
#     flood_viz_params = {
#         'palette': ['0000FF']  # Blue color for flooded areas
#     }
#     # Add the flood extent layer. selfMask() was applied earlier, so 0s are already transparent.
#     Map.addLayer(flood_extent_map, flood_viz_params, 'Flood Extent (New Water)')

#     # Optional: Add before and after Sentinel-1 VV images for context
#     # These are raw VV backscatter; lower values (darker) often indicate water or smooth surfaces.
#     s1_viz_params = {'min': -25, 'max': 0} # Typical VV visualization range in dB
#     Map.addLayer(s1_before, s1_viz_params, f'Sentinel-1 Before VV ({selected_orbit_pass})', False) # Initially not visible
#     Map.addLayer(s1_after, s1_viz_params, f'Sentinel-1 After VV ({selected_orbit_pass})', False)    # Initially not visible

#     # Optional: Add permanent water (water present in 'before' period)
#     permanent_water_viz_params = {'palette': ['ADD8E6']} # Light blue for permanent water
#     Map.addLayer(water_mask_before.selfMask(), permanent_water_viz_params, 'Permanent Water (Before)', False)

#     # Display the map in the Jupyter output
#     # display(Map) # In a Jupyter notebook, this command would render the interactive map.
#     print("Map object created. If running in Colab/Jupyter, uncomment 'display(Map)' to show it.")
#     print("Layers added: Flood Extent, S1 Before (optional), S1 After (optional), Permanent Water (optional).")

# except ImportError:
#     print("The 'geemap' library is not installed. Please install it (pip install geemap) to use map visualization features.")
# except Exception as e:
#     print(f"An error occurred during geemap visualization setup: {e}")
#     print("Ensure you are in a Jupyter-like environment and Earth Engine is initialized if 'geemap' is installed.")
# """

# --- Exporting the flood_extent_map ---
# The `flood_extent_map` is a binary image where 1 indicates flooded areas.
# The .toFloat() conversion is good practice for exports, though often not strictly necessary for binary.

# # --- Example 1: Export to Google Drive ---
# # User-configurable parameters:
# drive_folder_name = 'EarthEngineExports'      # Folder in your Google Drive
# drive_file_name_prefix = 'flood_naypyidaw_S1' # Base name for the exported file

# # Task configuration
# task_drive = ee.batch.Export.image.toDrive(
#     image=flood_extent_map.toFloat(), # .toFloat() is a safe practice
#     description='FloodMapExport_Naypyidaw_Drive',
#     folder=drive_folder_name,
#     fileNamePrefix=drive_file_name_prefix,
#     region=aoi.getInfo()['coordinates'], # Export the defined AOI
#     scale=10,  # Pixel size in meters. Sentinel-1 GRD native is ~10m.
#                # Higher scale (e.g., 30m) for faster exports if lower resolution is acceptable.
#     crs='EPSG:4326'  # Coordinate system (WGS84 is common for GeoTIFFs)
# )
# # # Start the export task (uncomment the line below to run)
# # task_drive.start()
# # print(f"Export task to Google Drive started (Folder: {drive_folder_name}, File: {drive_file_name_prefix}*).")
# # print("Check 'Tasks' tab in GEE Code Editor or use task_drive.status() to monitor.")


# # --- Example 2: Export as an Earth Engine Asset ---
# # User-configurable parameters:
# # IMPORTANT: Replace 'YOUR_EE_USERNAME_OR_PROJECT_PATH' with your EE username (e.g., 'users/username')
# # or an EE project path (e.g., 'projects/your-gcp-project-id/assets') where you have write access.
# ee_asset_path = 'users/YOUR_EE_USERNAME_OR_PROJECT_PATH/flood_maps' # Path for the asset
# ee_asset_name = 'naypyidaw_flood_S1_YYYYMMDD' # Name of the asset (append date or version)
# full_asset_id = f"{ee_asset_path}/{ee_asset_name}"

# # Task configuration
# task_asset = ee.batch.Export.image.toAsset(
#     image=flood_extent_map.toFloat(),
#     description='FloodMapExport_Naypyidaw_Asset',
#     assetId=full_asset_id,
#     region=aoi.getInfo()['coordinates'], # Export the defined AOI
#     scale=10, # For assets, exporting at native resolution (e.g., 10m for S1) is often preferred.
#     crs='EPSG:4326' # Or the projection of your choice (e.g., a UTM zone for specific regions)
# )
# # # Start the asset export task (uncomment the line below to run)
# # task_asset.start()
# # print(f"Export task to Earth Engine Asset started (Asset ID: {full_asset_id}).")
# # print("Check 'Tasks' tab in GEE Code Editor or use task_asset.status() to monitor.")

# # --- To monitor a task programmatically (optional, uncomment if a task was started) ---
# # import time
# # # Choose the task you want to monitor (e.g., task_drive or task_asset)
# # chosen_task = None # Example: chosen_task = task_drive
# #
# # if chosen_task:
# #     print(f"Monitoring task: {chosen_task.id}")
# #     while chosen_task.active():
# #         status = chosen_task.status()
# #         print(f"Polling for task (id: {chosen_task.id}). Status: {status['state']}")
# #         if status['state'] == 'FAILED':
# #             print(f"Error: {status['error_message']}")
# #             break
# #         time.sleep(30) # Wait 30 seconds before next poll
# #     if chosen_task.status()['state'] == 'COMPLETED':
# #         print(f"Task {chosen_task.id} finished: {chosen_task.status()['state']}")
# #     elif chosen_task.status()['state'] != 'FAILED':
# #         print(f"Task {chosen_task.id} status: {chosen_task.status()['state']}")
# # else:
# #     print("No export task was started or chosen for monitoring in the script.")

print("\nScript logic complete.")
print("Make sure Earth Engine is authenticated and initialized if you intend to run GEE operations.")
print("Review user-configurable parameters at the top of the script (AOI, dates, threshold).")
print("Uncomment visualization or export sections as needed and ensure necessary libraries (e.g., geemap) are installed.")
