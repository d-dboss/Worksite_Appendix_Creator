"""
Photo Appendix Generator - Map and Direction Generation Module
This module handles generating static map images and compass indicators.
"""
import os
import tempfile
import math
from PIL import Image, ImageDraw, ImageFont
import warnings
import requests # Import requests to potentially set User-Agent if needed later

# Import the staticmap library
try:
    from staticmap import StaticMap, CircleMarker, Line # Import Line if needed later
    STATICMAP_AVAILABLE = True
    print("staticmap library found. Map generation enabled.")
except ImportError:
    print("\n--- WARNING ---")
    print("'staticmap' library not found. Map generation will be skipped.")
    print("Install it using: pip install staticmap")
    print("Ensure you have an active internet connection for map generation.")
    print("---------------\n")
    STATICMAP_AVAILABLE = False

# Keep track of temporary files created *by this module* in a single run
_temp_files_this_run = []

def find_font(preferred_fonts=["Arial", "DejaVuSans", "Helvetica"], size=10):
     """Tries to find a suitable TTF font."""
     font_paths = [
         '/usr/share/fonts/truetype/dejavu/', # Linux DejaVu
         '/usr/share/fonts/truetype/msttcorefonts/', # Linux MS Core Fonts
         '/Library/Fonts/', # macOS System Fonts
         os.path.expanduser('~/Library/Fonts/'), # macOS User Fonts expanded
         'C:/Windows/Fonts/' # Windows
     ]
     for font_name in preferred_fonts:
         try:
             found_font = ImageFont.truetype(f"{font_name}.ttf", size)
             return found_font
         except IOError: pass
         for path_dir in font_paths:
             try:
                 font_file = os.path.join(path_dir, f"{font_name}.ttf")
                 if os.path.exists(font_file):
                     found_font = ImageFont.truetype(font_file, size)
                     return found_font
             except Exception: continue
     print(f"Warning: Could not find preferred fonts ({preferred_fonts}). Using default Pillow font.")
     try:
         font = ImageFont.load_default()
         return font
     except Exception as e:
         print(f"FATAL: Could not load default Pillow font: {e}")
         raise RuntimeError("Unable to load any fonts for image generation.")


DEFAULT_FONT_SMALL = find_font(size=9)
DEFAULT_FONT_NORMAL = find_font(size=10)
DEFAULT_FONT_COMPASS = find_font(size=11)


def generate_map_image(latitude, longitude, zoom=15, size=(180, 180)):
    """
    Generate a static map image for the given coordinates using OpenStreetMap data.

    Args:
        latitude (float): Latitude coordinate.
        longitude (float): Longitude coordinate.
        zoom (int): Zoom level for the map (default: 15).
        size (tuple): Size of the output image (width, height) in pixels.

    Returns:
        str: Path to the generated map image (temporary file) or None if failed.
    """
    global _temp_files_this_run

    if not STATICMAP_AVAILABLE:
        print("Skipping map generation: 'staticmap' library not available.")
        return None

    if latitude is None or longitude is None:
        print("Skipping map generation: Missing coordinates.")
        return None

    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        print(f"Skipping map generation: Invalid coordinates Lat={latitude}, Lon={longitude}")
        return None

    temp_img_path = None
    try:
        width, height = size
        print(f"  Attempting map generation for Lat={latitude:.5f}, Lon={longitude:.5f} (Zoom={zoom}, Size={width}x{height})")

        # ***** FIX: Changed the URL Template back to standard OSM tile server WITHOUT subdomain placeholder *****
        osm_url = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
        print(f"    Using tile server URL: {osm_url}")

        # Create StaticMap instance with the new URL
        # We also add a basic User-Agent header - THIS IS IMPORTANT for OSM policy
        headers = {'User-Agent': 'PhotoAppendixGenerator/1.0 (Python StaticMap Script; contact: jordantbeaumont@gmail.com)'} # REPLACE EMAIL
        map_instance = StaticMap(width, height, url_template=osm_url, headers=headers)


        # Add marker
        marker_coord = (longitude, latitude) # Longitude first
        marker = CircleMarker(marker_coord, 'red', 12)
        map_instance.add_marker(marker)

        # Render the map image object
        print("    Rendering map...")
        image = map_instance.render(zoom=zoom)
        print("    Map rendered.")

        # Save to a temporary PNG file
        temp_fd, temp_img_path = tempfile.mkstemp(suffix='.png')
        os.close(temp_fd)
        print(f"    Saving map to temporary file: {os.path.basename(temp_img_path)}")
        image.save(temp_img_path, 'PNG')
        print("    Map saved.")

        _temp_files_this_run.append(temp_img_path)
        return temp_img_path

    except Exception as e:
        print(f"  ERROR generating map image for ({latitude:.5f}, {longitude:.5f}): {type(e).__name__}: {str(e)}")
        # import traceback # Uncomment for detailed debugging if needed
        # print("  --- Map Generation Traceback ---")
        # traceback.print_exc()
        # print("  --------------------------------")

        if temp_img_path and os.path.exists(temp_img_path):
             try:
                 os.unlink(temp_img_path)
                 if temp_img_path in _temp_files_this_run: _temp_files_this_run.remove(temp_img_path)
             except OSError as cleanup_error:
                  print(f"  Warning: Could not clean up temp map file '{temp_img_path}' after error: {cleanup_error}")
        return None


# --- [ generate_compass_indicator and cleanup_temp_files remain the same as previous version ] ---
# --- [ Make sure they are present in your file ] ---
def generate_compass_indicator(orientation, size=(100, 100)):
    """
    Generate a compass direction indicator showing camera orientation heading.

    Args:
        orientation (float): Direction in degrees (0-360, 0/360=North).
        size (tuple): Size of the output image (width, height).

    Returns:
        str: Path to the generated compass image (temporary file) or None if failed.
    """
    global _temp_files_this_run

    if orientation is None:
        # print("Skipping compass generation: Orientation data is missing.") # Reduced verbosity
        return None

    # Validate orientation
    if not (0 <= orientation <= 360):
         print(f"Skipping compass generation: Invalid orientation value {orientation}")
         # Allow 360 as equivalent to 0 (North)
         if orientation % 360 == 0:
              orientation = 0
         else:
              return None


    temp_img_path = None # Initialize path
    try:
        # Create a new image with white background, use RGBA for potential transparency later
        img = Image.new('RGBA', size, (255, 255, 255, 255)) # White background
        draw = ImageDraw.Draw(img)

        # Center and Radius
        center_x, center_y = size[0] // 2, size[1] // 2
        margin = 15 # Margin for labels and text
        radius = min(center_x, center_y) - margin

        # --- Draw Compass Rose ---
        # Outer circle
        draw.ellipse([(center_x - radius, center_y - radius),
                      (center_x + radius, center_y + radius)],
                     outline=(100, 100, 100), width=1) # Gray outline

        # Tick marks (major and minor)
        for angle in range(0, 360, 15): # Ticks every 15 degrees
            angle_rad = math.radians(angle)
            is_major_cardinal = (angle % 90 == 0)
            is_minor_cardinal = (angle % 45 == 0) and not is_major_cardinal

            if is_major_cardinal:
                tick_len = 6
                tick_width = 2
                color = (0, 0, 0) # Black
            elif is_minor_cardinal:
                 tick_len = 4
                 tick_width = 1
                 color = (50, 50, 50) # Dark Gray
            else: # Minor ticks
                tick_len = 2
                tick_width = 1
                color = (150, 150, 150) # Light Gray

            inner_r = radius - tick_len
            outer_r = radius
            start_x = center_x + inner_r * math.sin(angle_rad)
            start_y = center_y - inner_r * math.cos(angle_rad)
            end_x = center_x + outer_r * math.sin(angle_rad)
            end_y = center_y - outer_r * math.cos(angle_rad)
            draw.line([(start_x, start_y), (end_x, end_y)], fill=color, width=tick_width)


        # Cardinal direction labels (N, E, S, W)
        font_labels = DEFAULT_FONT_COMPASS
        for dir_label, angle in [("N", 0), ("E", 90), ("S", 180), ("W", 270)]:
            angle_rad = math.radians(angle)
            label_dist = radius + 8 # Position labels just outside the circle
            label_x = center_x + label_dist * math.sin(angle_rad)
            label_y = center_y - label_dist * math.cos(angle_rad)

            # Use textbbox for better centering if available (Pillow >= 8)
            try:
                 bbox = draw.textbbox((0, 0), dir_label, font=font_labels)
                 text_width = bbox[2] - bbox[0]
                 text_height = bbox[3] - bbox[1]
            except AttributeError:
                 text_width, text_height = draw.textsize(dir_label, font=font_labels) # Fallback

            draw.text((label_x - text_width/2, label_y - text_height/2),
                     dir_label, fill=(0, 0, 0), font=font_labels)


        # --- Draw Orientation Arrow ---
        orientation_rad = math.radians(orientation)
        arrow_length = radius - 3 # Arrow stops just inside the circle
        arrow_color = (200, 0, 0, 255) # Opaque Red
        arrow_width = 2

        # Calculate arrow end point
        end_x = center_x + arrow_length * math.sin(orientation_rad)
        end_y = center_y - arrow_length * math.cos(orientation_rad)

        # Draw arrow line
        draw.line([(center_x, center_y), (end_x, end_y)], fill=arrow_color, width=arrow_width)

        # Draw arrow head (as a filled triangle)
        head_size = 8 # Size of the arrowhead base/height
        head_angle = math.radians(25) # Angle of the arrowhead sides

        # Points for the arrowhead polygon (relative to the arrow end point)
        angle1 = orientation_rad + math.pi - head_angle # Point 1 angle
        angle2 = orientation_rad + math.pi + head_angle # Point 2 angle

        head1_x = end_x + head_size * math.sin(angle1)
        head1_y = end_y - head_size * math.cos(angle1)
        head2_x = end_x + head_size * math.sin(angle2)
        head2_y = end_y - head_size * math.cos(angle2)

        # Draw filled polygon for arrowhead
        draw.polygon([(end_x, end_y), (head1_x, head1_y), (head2_x, head2_y)], fill=arrow_color)


        # --- Draw Central Hub ---
        hub_radius = 3
        draw.ellipse([(center_x - hub_radius, center_y - hub_radius),
                      (center_x + hub_radius, center_y + hub_radius)],
                     fill=(255, 255, 255), outline=(50, 50, 50), width=1)


        # --- Add Orientation Text ---
        font_text = DEFAULT_FONT_NORMAL
        orientation_text = f"{orientation:.0f}°" # Show whole degrees
         # Calculate text position below the compass
        try:
             bbox = draw.textbbox((0, 0), orientation_text, font=font_text)
             text_width = bbox[2] - bbox[0]
        except AttributeError:
             text_width, _ = draw.textsize(orientation_text, font=font_text) # Fallback

        text_y_pos = center_y + radius + 5 # Position text below the circle
        draw.text((center_x - text_width//2, text_y_pos),
                  orientation_text, fill=(0, 0, 0), font=font_text)


        # --- Save to Temporary File ---
        temp_fd, temp_img_path = tempfile.mkstemp(suffix='.png')
        os.close(temp_fd)
        img.save(temp_img_path, 'PNG')

        # Keep track for cleanup
        _temp_files_this_run.append(temp_img_path)

        # print(f"Generated compass indicator for {orientation:.1f}° at {temp_img_path}") # Reduced verbosity
        return temp_img_path

    except Exception as e:
        print(f"ERROR generating compass indicator for {orientation}°: {str(e)}")
        # Attempt cleanup if file was created
        if temp_img_path and os.path.exists(temp_img_path):
             try:
                 os.unlink(temp_img_path)
                 if temp_img_path in _temp_files_this_run:
                     _temp_files_this_run.remove(temp_img_path)
             except OSError as cleanup_error:
                 print(f"Warning: Could not clean up temp compass file '{temp_img_path}' after error: {cleanup_error}")
        return None


def cleanup_temp_files(file_paths=None):
    """
    Clean up temporary map/compass files created by this module during the current run.
    Can also clean up additional paths if passed.
    """
    global _temp_files_this_run
    paths_to_clean = set(_temp_files_this_run) # Use set to avoid duplicates

    # Add any explicitly passed file paths (might overlap, set handles that)
    if file_paths and isinstance(file_paths, (list, tuple)):
        for p in file_paths:
            if p: paths_to_clean.add(p)

    if not paths_to_clean:
        # print("No map/compass temporary files to clean up.") # Reduced verbosity
        return

    print(f"Cleaning up {len(paths_to_clean)} temporary map/compass file(s)...")
    cleaned_count = 0
    for path in paths_to_clean:
        if path and os.path.exists(path):
            try:
                os.unlink(path)
                # print(f"  - Cleaned: {path}") # Reduced verbosity
                cleaned_count += 1
            except Exception as e:
                print(f"ERROR: Failed to remove temp file '{path}': {str(e)}")

    if cleaned_count > 0:
         print(f"Successfully cleaned {cleaned_count} map/compass temporary file(s).")

    # Reset the list for the next potential run within the same app instance
    _temp_files_this_run = []