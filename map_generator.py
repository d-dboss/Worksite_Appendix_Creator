"""
Photo Appendix Generator - Map and Direction Generation Module
This module handles creating maps and compass direction indicators.
"""
import os
import io
import math
import tempfile
from PIL import Image, ImageDraw, ImageFont

def generate_map(latitude, longitude, zoom=15, size=(200, 200)):
    """
    Generate a map image with a pin at the specified coordinates.
    
    Args:
        latitude (float): Latitude coordinate
        longitude (float): Longitude coordinate
        zoom (int): Zoom level for the map (default: 15)
        size (tuple): Size of the output image (width, height)
        
    Returns:
        str: Path to the generated map image (temporary file)
    """
    try:
        # Create a nicer placeholder map image
        width, height = size
        img = Image.new('RGB', size, (240, 248, 255))  # Light blue background
        draw = ImageDraw.Draw(img)
        
        # Define colors
        water_color = (173, 216, 230)  # Light blue for water
        land_color = (240, 240, 224)   # Light tan for land
        road_color = (255, 255, 255)   # White for roads
        grid_color = (200, 200, 200)   # Light gray for grid
        text_color = (80, 80, 80)      # Dark gray for text
        pin_color = (255, 0, 0)        # Red for pin
        
        # Try to load a font, fall back to default if not available
        try:
            font = ImageFont.truetype("Arial", 12)
            small_font = ImageFont.truetype("Arial", 8)
        except IOError:
            font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Draw a nice background with some map features
        # Land mass (simplified representation)
        land_shape = [
            (0, height//2), 
            (width//4, height//2-20),
            (width//2, height//2-10),
            (3*width//4, height//2+15),
            (width, height//2+5),
            (width, height),
            (0, height)
        ]
        draw.polygon(land_shape, fill=land_color)
        
        # Water
        water_shape = [
            (0, 0),
            (width, 0),
            (width, height//2+5),
            (3*width//4, height//2+15),
            (width//2, height//2-10),
            (width//4, height//2-20),
            (0, height//2)
        ]
        draw.polygon(water_shape, fill=water_color)
        
        # Draw grid lines (lat/long grid)
        for i in range(0, width, width//8):
            draw.line([(i, 0), (i, height)], fill=grid_color, width=1)
        
        for i in range(0, height, height//8):
            draw.line([(0, i), (width, i)], fill=grid_color, width=1)
            
        # Draw a few "roads"
        draw.line([(width//4, 0), (width//4, height)], fill=road_color, width=2)
        draw.line([(0, height//3), (width, height//3)], fill=road_color, width=2)
        draw.line([(width//2, 0), (3*width//4, height)], fill=road_color, width=2)
        
        # Draw a border
        draw.rectangle([(0, 0), (width-1, height-1)], outline=(0, 0, 0), width=2)
        
        # Calculate position for the pin (center of the image)
        pin_x, pin_y = width // 2, height // 2
        
        # Draw a nicer pin
        pin_radius = 6
        # Draw a shadow
        draw.ellipse([(pin_x-pin_radius+2, pin_y-pin_radius+2), 
                      (pin_x+pin_radius+2, pin_y+pin_radius+2)], 
                     fill=(100, 100, 100))
        # Draw the pin circle
        draw.ellipse([(pin_x-pin_radius, pin_y-pin_radius), 
                      (pin_x+pin_radius, pin_y+pin_radius)], 
                     fill=pin_color, outline=(0, 0, 0))
        # Draw a small white dot in the center
        draw.ellipse([(pin_x-2, pin_y-2), (pin_x+2, pin_y+2)], fill=(255, 255, 255))
        
        # Add title
        title = "Location Map"
        title_width = draw.textlength(title, font=font)
        draw.text((width//2 - title_width//2, 5), title, fill=text_color, font=font)
        
        # Format coordinates to a reasonable precision
        lat_str = f"Lat: {latitude:.6f}"
        lon_str = f"Lon: {longitude:.6f}"
        
        # Add coordinates at the bottom
        lat_width = draw.textlength(lat_str, font=small_font)
        lon_width = draw.textlength(lon_str, font=small_font)
        
        draw.text((width//2 - lat_width//2, height-25), lat_str, fill=text_color, font=small_font)
        draw.text((width//2 - lon_width//2, height-15), lon_str, fill=text_color, font=small_font)
        
        # Add compass rose in corner
        compass_radius = 15
        compass_x, compass_y = width - compass_radius - 10, compass_radius + 10
        # Draw compass circle
        draw.ellipse([(compass_x-compass_radius, compass_y-compass_radius),
                      (compass_x+compass_radius, compass_y+compass_radius)],
                     outline=text_color, width=1)
        # Draw N-S-E-W lines
        draw.line([(compass_x, compass_y-compass_radius+3), (compass_x, compass_y+compass_radius-3)], 
                 fill=text_color, width=1)
        draw.line([(compass_x-compass_radius+3, compass_y), (compass_x+compass_radius-3, compass_y)], 
                 fill=text_color, width=1)
        # Add N-E-S-W labels
        draw.text((compass_x-3, compass_y-compass_radius-8), "N", fill=text_color, font=small_font)
        draw.text((compass_x+compass_radius+2, compass_y-3), "E", fill=text_color, font=small_font)
        draw.text((compass_x-3, compass_y+compass_radius+2), "S", fill=text_color, font=small_font)
        draw.text((compass_x-compass_radius-8, compass_y-3), "W", fill=text_color, font=small_font)
        
        # Add zoom indicator
        zoom_text = f"Zoom: {zoom}x"
        draw.text((10, 10), zoom_text, fill=text_color, font=small_font)
        
        # Save to temporary file
        temp_img = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        temp_img.close()
        img.save(temp_img.name)
        
        return temp_img.name
        
    except Exception as e:
        print(f"Error generating map: {str(e)}")
        return None

def generate_compass_indicator(orientation, size=(100, 100)):
    """
    Generate a compass direction indicator showing orientation.
    
    Args:
        orientation (float): Direction in degrees (0-360, 0/360=North, 90=East, etc.)
        size (tuple): Size of the output image (width, height)
        
    Returns:
        str: Path to the generated compass image (temporary file)
    """
    try:
        # Create a new image with white background
        img = Image.new('RGB', size, (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        # Calculate center of the image
        center_x, center_y = size[0] // 2, size[1] // 2
        
        # Calculate radius (slightly smaller than half the smallest dimension)
        radius = min(center_x, center_y) - 10
        
        # Draw outer circle
        draw.ellipse([(center_x - radius, center_y - radius), 
                      (center_x + radius, center_y + radius)], 
                     outline=(0, 0, 0), width=2)
        
        # Draw cardinal directions
        try:
            font = ImageFont.truetype("Arial", 12)
        except IOError:
            font = ImageFont.load_default()
            
        # North
        draw.text((center_x - 5, center_y - radius - 15), "N", fill=(0, 0, 0), font=font)
        # East
        draw.text((center_x + radius + 5, center_y - 5), "E", fill=(0, 0, 0), font=font)
        # South
        draw.text((center_x - 5, center_y + radius + 5), "S", fill=(0, 0, 0), font=font)
        # West
        draw.text((center_x - radius - 15, center_y - 5), "W", fill=(0, 0, 0), font=font)
        
        # Convert orientation to radians
        orientation_rad = math.radians(orientation)
        
        # Calculate end point of the arrow
        arrow_length = radius - 5
        end_x = center_x + arrow_length * math.sin(orientation_rad)
        end_y = center_y - arrow_length * math.cos(orientation_rad)
        
        # Draw the direction arrow
        arrow_width = 3
        draw.line([(center_x, center_y), (end_x, end_y)], fill=(255, 0, 0), width=arrow_width)
        
        # Draw arrow head
        head_size = 10
        head_angle = math.pi / 6  # 30 degrees
        
        # Calculate points for arrow head
        angle1 = orientation_rad + math.pi - head_angle
        angle2 = orientation_rad + math.pi + head_angle
        
        head1_x = end_x + head_size * math.sin(angle1)
        head1_y = end_y - head_size * math.cos(angle1)
        
        head2_x = end_x + head_size * math.sin(angle2)
        head2_y = end_y - head_size * math.cos(angle2)
        
        # Draw arrow head
        draw.line([(end_x, end_y), (head1_x, head1_y)], fill=(255, 0, 0), width=arrow_width)
        draw.line([(end_x, end_y), (head2_x, head2_y)], fill=(255, 0, 0), width=arrow_width)
        
        # Add orientation text
        orientation_text = f"{orientation:.1f}°"
        text_width = draw.textlength(orientation_text, font=font)
        draw.text((center_x - text_width/2, center_y + radius + 20), 
                  orientation_text, fill=(0, 0, 0), font=font)
        
        # Save to temporary file
        temp_img = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        temp_img.close()
        img.save(temp_img.name)
        
        return temp_img.name
        
    except Exception as e:
        print(f"Error generating compass indicator: {str(e)}")
        return None

def cleanup_temp_files(file_paths):
    """
    Clean up temporary files created during map and compass generation.
    
    Args:
        file_paths (list): List of file paths to remove
    """
    if not file_paths:
        return
        
    for path in file_paths:
        if path and os.path.exists(path):
            try:
                os.unlink(path)
            except Exception as e:
                print(f"Error removing temp file {path}: {str(e)}")
