"""
Photo Appendix Generator - Map and Direction Generation Module
This module handles creating maps and compass direction indicators using OpenStreetMap data via Overpass API.
"""
import os
import io
import math
import tempfile
import requests
import json
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import urllib.parse
import time
import random

# List of available Overpass API endpoints
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",       # Main instance
    "https://overpass.private.coffee/api/interpreter",  # Private.coffee instance
    "https://overpass.osm.jp/api/interpreter",       # Japan instance
    "https://overpass.openstreetmap.ru/api/interpreter"  # Russian instance
]

def get_available_endpoint():
    """
    Get a random available Overpass API endpoint to distribute load.
    Returns:
        str: URL of an available Overpass API endpoint
    """
    # Start with the main endpoint as default
    endpoint = OVERPASS_ENDPOINTS[0]
    
    # Try a random endpoint to distribute load
    try:
        endpoint = random.choice(OVERPASS_ENDPOINTS)
    except:
        pass
        
    return endpoint

def build_overpass_query(latitude, longitude, radius=100):
    """
    Build an Overpass API query to get map features around a location.
    
    Args:
        latitude (float): Latitude coordinate
        longitude (float): Longitude coordinate
        radius (int): Radius in meters around the point
        
    Returns:
        str: Overpass QL query
    """
    # Create a query for roads, buildings, water, and other major features
    query = f"""
    [out:json][timeout:25];
    (
      way(around:{radius},{latitude},{longitude})[highway];
      way(around:{radius},{latitude},{longitude})[building];
      way(around:{radius},{latitude},{longitude})[natural=water];
      way(around:{radius},{latitude},{longitude})[landuse];
      way(around:{radius},{latitude},{longitude})[amenity];
      node(around:{radius},{latitude},{longitude})[amenity];
      node(around:{radius},{latitude},{longitude})[shop];
      node(around:{radius},{latitude},{longitude})[tourism];
    );
    out body geom;
    """
    return query

def get_map_data_from_overpass(latitude, longitude, radius=100):
    """
    Get map data from Overpass API.
    
    Args:
        latitude (float): Latitude coordinate
        longitude (float): Longitude coordinate
        radius (int): Radius in meters around the point
        
    Returns:
        dict: JSON response from Overpass API or None if failed
    """
    try:
        # Build the query
        query = build_overpass_query(latitude, longitude, radius)
        
        # Get an available endpoint
        endpoint = get_available_endpoint()
        
        # Make the request to Overpass API
        print(f"Querying Overpass API ({endpoint}) for location: {latitude}, {longitude}")
        response = requests.post(
            endpoint,
            data={"data": query},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30
        )
        
        # Check if the request was successful
        if response.status_code == 200:
            data = response.json()
            print(f"Successfully retrieved data with {len(data.get('elements', []))} elements")
            return data
        else:
            print(f"Overpass API request failed with status code: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error getting data from Overpass API: {str(e)}")
        return None

def render_map_from_overpass_data(data, latitude, longitude, size=(300, 300), zoom_factor=1.0):
    """
    Render a map image from Overpass API data.
    
    Args:
        data (dict): JSON response from Overpass API
        latitude (float): Center latitude
        longitude (float): Center longitude
        size (tuple): Size of the output image (width, height)
        zoom_factor (float): Zoom level factor (higher = more zoomed in)
        
    Returns:
        PIL.Image: Rendered map image
    """
    if not data or 'elements' not in data:
        return None
        
    width, height = size
    
    # Create a new blank image
    img = Image.new('RGB', size, (240, 248, 255))  # Light blue background
    draw = ImageDraw.Draw(img)
    
    # Calculate bounding box from the data
    min_lat, max_lat, min_lon, max_lon = float('inf'), float('-inf'), float('inf'), float('-inf')
    
    for element in data.get('elements', []):
        if element['type'] == 'way' and 'geometry' in element:
            for point in element['geometry']:
                min_lat = min(min_lat, point['lat'])
                max_lat = max(max_lat, point['lat'])
                min_lon = min(min_lon, point['lon'])
                max_lon = max(max_lon, point['lon'])
    
    # If we couldn't determine bounds from elements, use a default area around the center
    if min_lat == float('inf'):
        min_lat = latitude - 0.003 / zoom_factor
        max_lat = latitude + 0.003 / zoom_factor
        min_lon = longitude - 0.003 / zoom_factor
        max_lon = longitude + 0.003 / zoom_factor
    
    # Add a small buffer around the bounds
    buffer_lat = (max_lat - min_lat) * 0.1
    buffer_lon = (max_lon - min_lon) * 0.1
    min_lat -= buffer_lat
    max_lat += buffer_lat
    min_lon -= buffer_lon
    max_lon += buffer_lon
    
    # Function to convert lat/lon to pixel coordinates
    def latlon_to_pixel(lat, lon):
        x = int((lon - min_lon) / (max_lon - min_lon) * width)
        y = int((max_lat - lat) / (max_lat - min_lat) * height)
        return (x, y)
    
    # Draw a grid for reference
    grid_color = (200, 200, 200)
    for i in range(0, width, width//8):
        draw.line([(i, 0), (i, height)], fill=grid_color, width=1)
    
    for i in range(0, height, height//8):
        draw.line([(0, i), (width, i)], fill=grid_color, width=1)
    
    # Render different elements with different styles
    for element in data.get('elements', []):
        if element['type'] == 'way' and 'geometry' in element:
            points = [latlon_to_pixel(point['lat'], point['lon']) for point in element['geometry']]
            
            if len(points) < 2:
                continue
                
            # Choose color based on element tags
            tags = element.get('tags', {})
            color = (100, 100, 100)  # Default color
            width = 1  # Default width
            fill = None  # Default fill
            
            if 'highway' in tags:
                highway_type = tags['highway']
                if highway_type in ['motorway', 'trunk', 'primary']:
                    color = (255, 0, 0)  # Red
                    width = 3
                elif highway_type in ['secondary', 'tertiary']:
                    color = (255, 165, 0)  # Orange
                    width = 2
                else:
                    color = (255, 255, 255)  # White
                    width = 2
            elif 'building' in tags:
                color = (169, 169, 169)  # Gray
                fill = (169, 169, 169, 128)  # Semi-transparent gray
            elif 'natural' in tags and tags['natural'] == 'water':
                color = (0, 191, 255)  # Deep sky blue
                fill = (0, 191, 255, 150)  # Semi-transparent blue
            elif 'landuse' in tags:
                if tags['landuse'] in ['forest', 'wood']:
                    color = (34, 139, 34)  # Forest green
                    fill = (34, 139, 34, 150)  # Semi-transparent green
                elif tags['landuse'] in ['residential', 'commercial']:
                    color = (245, 222, 179)  # Tan
                    fill = (245, 222, 179, 150)  # Semi-transparent tan
            
            # Draw the element
            if fill:
                # For filled areas like buildings, water, landuse
                try:
                    draw.polygon(points, outline=color, fill=fill)
                except:
                    # If polygon fails, try with a line
                    try:
                        draw.line(points, fill=color, width=width)
                    except:
                        pass
            else:
                # For lines like highways
                try:
                    draw.line(points, fill=color, width=width)
                except:
                    pass
    
    # Draw a marker at the center point
    center_pixel = latlon_to_pixel(latitude, longitude)
    marker_radius = 8
    
    # Draw shadow
    draw.ellipse([
        (center_pixel[0] - marker_radius + 2, center_pixel[1] - marker_radius + 2),
        (center_pixel[0] + marker_radius + 2, center_pixel[1] + marker_radius + 2)
    ], fill=(100, 100, 100))
    
    # Draw red pin
    draw.ellipse([
        (center_pixel[0] - marker_radius, center_pixel[1] - marker_radius),
        (center_pixel[0] + marker_radius, center_pixel[1] + marker_radius)
    ], fill=(255, 0, 0), outline=(0, 0, 0))
    
    # Draw white dot in center
    draw.ellipse([
        (center_pixel[0] - 2, center_pixel[1] - 2),
        (center_pixel[0] + 2, center_pixel[1] + 2)
    ], fill=(255, 255, 255))
    
    # Add coordinates and attribution
    try:
        font = ImageFont.truetype("Arial", 10)
        small_font = ImageFont.truetype("Arial", 8)
    except IOError:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # Add coordinates
    coords_text = f"Lat: {latitude:.6f}, Lon: {longitude:.6f}"
    text_bbox = draw.textbbox((0, 0), coords_text, font=small_font)
    text_width = text_bbox[2] - text_bbox[0]
    draw.rectangle([(5, height - 25), (text_width + 15, height - 5)], fill=(255, 255, 255, 180))
    draw.text((10, height - 20), coords_text, fill=(0, 0, 0), font=small_font)
    
    # Add attribution (required for OpenStreetMap data)
    attribution = "© OpenStreetMap contributors"
    text_bbox = draw.textbbox((0, 0), attribution, font=small_font)
    text_width = text_bbox[2] - text_bbox[0]
    draw.rectangle([(width - text_width - 15, height - 25), (width - 5, height - 5)], fill=(255, 255, 255, 180))
    draw.text((width - text_width - 10, height - 20), attribution, fill=(0, 0, 0), font=small_font)
    
    # Draw a border around the map
    draw.rectangle([(0, 0), (width-1, height-1)], outline=(0, 0, 0), width=2)
    
    return img

def generate_map(latitude, longitude, zoom=14, size=(300, 300)):
    """
    Generate a map image with a pin at the specified coordinates using OpenStreetMap data via Overpass API.
    
    Args:
        latitude (float): Latitude coordinate
        longitude (float): Longitude coordinate
        zoom (int): Zoom level for the map (default: 14)
        size (tuple): Size of the output image (width, height)
        
    Returns:
        str: Path to the generated map image (temporary file)
    """
    try:
        print(f"Generating map for coordinates: Lat {latitude}, Lon {longitude}")
        
        # Calculate radius based on zoom level (higher zoom = smaller radius)
        radius = int(500 / (zoom / 10))  # Base radius of 500m at zoom level 10
        
        # Get map data from Overpass API
        map_data = get_map_data_from_overpass(latitude, longitude, radius)
        
        if map_data:
            # Render the map from the data
            zoom_factor = zoom / 10.0  # Normalize zoom factor
            map_img = render_map_from_overpass_data(map_data, latitude, longitude, size, zoom_factor)
            
            if map_img:
                # Save to temporary file
                temp_img = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                temp_img.close()
                map_img.save(temp_img.name)
                
                print(f"Successfully generated map: {temp_img.name}")
                return temp_img.name
        
        # If we get here, either the API request failed or rendering failed
        print("Falling back to placeholder map")
        return generate_placeholder_map(latitude, longitude, zoom, size)
        
    except Exception as e:
        print(f"Error generating map: {str(e)}")
        return generate_placeholder_map(latitude, longitude, zoom, size)

def generate_placeholder_map(latitude, longitude, zoom=14, size=(300, 300)):
    """
    Generate a placeholder map image when Overpass API is unavailable.
    
    Args:
        latitude (float): Latitude coordinate
        longitude (float): Longitude coordinate
        zoom (int): Zoom level for the map (default: 14)
        size (tuple): Size of the output image (width, height)
        
    Returns:
        str: Path to the generated map image (temporary file)
    """
    try:
        print(f"Generating placeholder map for: Lat {latitude}, Lon {longitude}")
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
        title = "Location Map (Offline)"
        text_bbox = draw.textbbox((0, 0), title, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        draw.text((width//2 - text_width//2, 5), title, fill=text_color, font=font)
        
        # Format coordinates to a reasonable precision
        lat_str = f"Lat: {latitude:.6f}"
        lon_str = f"Lon: {longitude:.6f}"
        
        # Add coordinates at the bottom
        text_bbox = draw.textbbox((0, 0), lat_str, font=small_font)
        lat_width = text_bbox[2] - text_bbox[0]
        text_bbox = draw.textbbox((0, 0), lon_str, font=small_font)
        lon_width = text_bbox[2] - text_bbox[0]
        
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
        
        # Add attribution
        attribution = "© OpenStreetMap contributors"
        text_bbox = draw.textbbox((0, 0), attribution, font=small_font)
        text_width = text_bbox[2] - text_bbox[0]
        draw.text((width - text_width - 5, height - 15), attribution, fill=text_color, font=small_font)
        
        # Save to temporary file
        temp_img = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        temp_img.close()
        img.save(temp_img.name)
        
        return temp_img.name
        
    except Exception as e:
        print(f"Error generating placeholder map: {str(e)}")
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
        text_bbox = draw.textbbox((0, 0), orientation_text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        draw.text((center_x - text_width//2, center_y + radius + 20), 
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
