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

def get_map_data_from_overpass(latitude, longitude, radius=300):
    """
    Get map data from Overpass API with improved error handling and logging.
    
    Args:
        latitude (float): Latitude coordinate
        longitude (float): Longitude coordinate
        radius (int): Radius in meters around the point
        
    Returns:
        dict: JSON response from Overpass API or None if failed
    """
    """
    Get map data from Overpass API with improved error handling and logging.
    
    Args:
        latitude (float): Latitude coordinate
        longitude (float): Longitude coordinate
        radius (int): Radius in meters around the point
        
    Returns:
        dict: JSON response from Overpass API or None if failed
    """
    try:
        # Build the query - simplified to focus on the most essential features
        query = f"""
        [out:json][timeout:60];
        (
          way(around:{radius},{latitude},{longitude})[highway];
          way(around:{radius},{latitude},{longitude})[building];
          way(around:{radius},{latitude},{longitude})[waterway];
          way(around:{radius},{latitude},{longitude})[natural];
          way(around:{radius},{latitude},{longitude})[landuse];
          way(around:{radius},{latitude},{longitude})[water];
          rel(around:{radius},{latitude},{longitude})[landuse];
          rel(around:{radius},{latitude},{longitude})[natural];
        );
        out body geom;
        """
        
        print(f"Attempting to fetch map data for coordinates: Lat {latitude}, Lon {longitude}")
        
        # Endpoints to try, in order of preference
        endpoints = [
            "https://overpass-api.de/api/interpreter",
            "https://overpass.private.coffee/api/interpreter", 
            "https://overpass.osm.jp/api/interpreter",
            "https://overpass.openstreetmap.ru/api/interpreter"
        ]
        
        # Try each endpoint until one works
        response = None
        for endpoint in endpoints:
            try:
                print(f"Trying Overpass API endpoint: {endpoint}")
                response = requests.post(
                    endpoint,
                    data={"data": query},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=30  # Set a reasonable timeout
                )
                
                if response.status_code == 200:
                    print(f"Successfully connected to {endpoint}")
                    break
                else:
                    print(f"Endpoint {endpoint} returned status code: {response.status_code}")
                    # Add delay to avoid rate limiting
                    time.sleep(1)
            except Exception as e:
                print(f"Error with endpoint {endpoint}: {str(e)}")
                # Add delay to avoid rate limiting
                time.sleep(1)
                continue
        
        # Check if we got a successful response
        if response and response.status_code == 200:
            try:
                data = response.json()
                element_count = len(data.get('elements', []))
                print(f"Successfully retrieved data with {element_count} elements")
                
                if element_count == 0:
                    print("Warning: No map elements returned for this location")
                
                return data
            except Exception as e:
                print(f"Error parsing JSON response: {str(e)}")
                if response.text:
                    print(f"Response text: {response.text[:200]}...")  # Print first 200 chars
                return None
        else:
            status = response.status_code if response else "No response"
            print(f"All Overpass API endpoints failed. Last status: {status}")
            return None
            
    except Exception as e:
        print(f"Error getting data from Overpass API: {str(e)}")
        return None

def render_map_from_overpass_data(data, latitude, longitude, size=(300, 300), zoom_factor=1.0):
    """
    Render a map image from Overpass API data with improved visibility.
    
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
    
    # Create a new blank image with a light background
    bg_color = (240, 245, 250)  # Light blue-gray
    img = Image.new('RGB', size, bg_color)
    draw = ImageDraw.Draw(img)
    
    # Calculate bounding box from the data
    min_lat, max_lat, min_lon, max_lon = float('inf'), float('-inf'), float('inf'), float('-inf')
    
    # First pass to determine bounds
    for element in data.get('elements', []):
        if element['type'] == 'way' and 'geometry' in element:
            for point in element['geometry']:
                min_lat = min(min_lat, point['lat'])
                max_lat = max(max_lat, point['lat'])
                min_lon = min(min_lon, point['lon'])
                max_lon = max(max_lon, point['lon'])
    
    # If we couldn't determine bounds from elements, use a default area around the center
    if min_lat == float('inf'):
        # Default view
        view_range = 0.005 / zoom_factor
        min_lat = latitude - view_range
        max_lat = latitude + view_range
        min_lon = longitude - view_range
        max_lon = longitude + view_range
    
    # Force the photo coordinates to be exactly at center of the map
    lat_range = max_lat - min_lat
    lon_range = max_lon - min_lon
    
    min_lat = latitude - lat_range / 2
    max_lat = latitude + lat_range / 2
    min_lon = longitude - lon_range / 2
    max_lon = longitude + lon_range / 2
    
    # Add a small buffer
    buffer_lat = lat_range * 0.1
    buffer_lon = lon_range * 0.1
    min_lat -= buffer_lat
    max_lat += buffer_lat
    min_lon -= buffer_lon
    max_lon += buffer_lon
    
    # Function to convert lat/lon to pixel coordinates
    def latlon_to_pixel(lat, lon):
        x = int((lon - min_lon) / (max_lon - min_lon) * width)
        y = int((max_lat - lat) / (max_lat - min_lat) * height)
        return (x, y)
    
    # Define simple, clear color scheme
    colors = {
        'water': (170, 211, 223),       # Blue
        'waterway': (170, 211, 223),    # Blue
        'natural': (200, 250, 204),     # Light green
        'forest': (173, 209, 158),      # Medium green
        'residential': (242, 239, 233), # Light tan
        'building': (200, 200, 200),    # Gray
        'highway': {
            'motorway': (255, 155, 120),    # Reddish
            'trunk': (255, 187, 120),       # Orange
            'primary': (255, 187, 120),     # Orange
            'secondary': (252, 246, 130),   # Yellow
            'tertiary': (255, 255, 255),    # White
            'residential': (255, 255, 255), # White
            'service': (255, 255, 255),     # White
            'default': (255, 255, 255)      # White
        }
    }
    
    # Process elements by type for layered rendering
    landuse_elements = []
    water_elements = []
    waterway_elements = []
    natural_elements = []
    highways = []
    buildings = []
    other_elements = []
    
    for element in data.get('elements', []):
        if element['type'] == 'way' and 'geometry' in element:
            tags = element.get('tags', {})
            if 'landuse' in tags:
                landuse_elements.append(element)
            elif 'natural' in tags and tags['natural'] == 'water':
                water_elements.append(element)
            elif 'waterway' in tags:
                waterway_elements.append(element)
            elif 'natural' in tags:
                natural_elements.append(element)
            elif 'highway' in tags:
                highways.append(element)
            elif 'building' in tags:
                buildings.append(element)
            else:
                other_elements.append(element)
    
    # Render layers from background to foreground
    
    # Draw a subtle grid for reference
    grid_color = (220, 220, 220)
    for i in range(0, width, width//10):
        draw.line([(i, 0), (i, height)], fill=grid_color, width=1)
    
    for i in range(0, height, height//10):
        draw.line([(0, i), (width, i)], fill=grid_color, width=1)
    
    # 1. Landuse (background)
    for element in landuse_elements:
        points = [latlon_to_pixel(point['lat'], point['lon']) for point in element['geometry']]
        if len(points) < 3:
            continue
            
        tags = element.get('tags', {})
        landuse_type = tags.get('landuse', '')
        
        # Choose colors based on landuse type
        if landuse_type in ['forest', 'wood']:
            color = (34, 139, 34)  # Forest green
            fill = (34, 139, 34)
        elif landuse_type in ['residential', 'commercial']:
            color = (245, 222, 179)  # Tan
            fill = (245, 222, 179)
        elif landuse_type in ['farmland', 'farm', 'meadow']:
            color = (173, 209, 158)  # Light green
            fill = (173, 209, 158)
        elif landuse_type in ['industrial']:
            color = (209, 198, 207)  # Light purple-gray
            fill = (209, 198, 207)
        else:
            color = (200, 200, 200)  # Default gray
            fill = (200, 200, 200)
        
        # Draw the polygon - with improved handling to prevent diagonal artifacts
        try:
            # Check if the polygon's first and last points match (closed shape)
            if len(points) > 3:  # Need at least 3 points for a valid polygon
                # Make a copy of the points list to avoid modifying the original
                drawing_points = list(points)
                
                # Ensure the polygon is closed (first and last points match)
                if drawing_points[0] != drawing_points[-1]:
                    drawing_points.append(drawing_points[0])
                
                # Remove any duplicate adjacent points that might cause rendering issues
                cleaned_points = [drawing_points[0]]
                for i in range(1, len(drawing_points)):
                    if drawing_points[i] != cleaned_points[-1]:
                        cleaned_points.append(drawing_points[i])
                
                # Only draw if we have enough points for a valid polygon
                if len(cleaned_points) >= 3:
                    draw.polygon(cleaned_points, outline=color, fill=fill)
                else:
                    # Fall back to drawing lines if not enough points for a polygon
                    draw.line(points, fill=color, width=1)
            else:
                # Not enough points for a polygon, draw lines instead
                draw.line(points, fill=color, width=1)
        except Exception as e:
            print(f"Error drawing polygon: {str(e)}")
            # Fall back to drawing lines
            try:
                draw.line(points, fill=color, width=1)
            except:
                pass
    
    # 2. Natural features and water
    for element in natural_elements:
        points = [latlon_to_pixel(point['lat'], point['lon']) for point in element['geometry']]
        if len(points) < 2:
            continue
            
        tags = element.get('tags', {})
        natural_type = tags.get('natural', '')
        
        # Choose colors based on natural type
        if natural_type == 'water':
            color = (0, 112, 184)  # Blue
            fill = (0, 132, 204)  # Semi-transparent blue
        elif natural_type in ['wood', 'tree', 'forest']:
            color = (12, 128, 44)  # Dark green
            fill = (12, 128, 44)  # Semi-transparent green
        elif natural_type in ['grassland', 'heath']:
            color = (122, 184, 95)  # Light green
            fill = (122, 184, 95)  # Semi-transparent light green
        elif natural_type in ['cliff', 'ridge', 'scree']:
            color = (140, 120, 100)  # Brown
            fill = (140, 120, 100)  # Semi-transparent brown
        else:
            color = (120, 160, 120)  # Default green
            fill = (120, 160, 120)  # Semi-transparent green
        
        # Draw the element
        if len(points) > 2:
            try:
                draw.polygon(points, outline=color, fill=fill)
            except:
                try:
                    draw.line(points, fill=color, width=2)
                except:
                    pass
        else:
            try:
                draw.line(points, fill=color, width=2)
            except:
                pass
    
    # 3. Water bodies
    for element in water_elements:
        points = [latlon_to_pixel(point['lat'], point['lon']) for point in element['geometry']]
        if len(points) < 3:
            continue
            
        # Draw water body - with improved handling to prevent diagonal artifacts
        try:
            # Check if we have enough points and ensure the polygon is closed
            if len(points) > 3:
                # Make a copy of the points list to avoid modifying the original
                drawing_points = list(points)
                
                # Ensure the polygon is closed (first and last points match)
                if drawing_points[0] != drawing_points[-1]:
                    drawing_points.append(drawing_points[0])
                
                # Remove any duplicate adjacent points that might cause rendering issues
                cleaned_points = [drawing_points[0]]
                for i in range(1, len(drawing_points)):
                    if drawing_points[i] != cleaned_points[-1]:
                        cleaned_points.append(drawing_points[i])
                
                # Only draw if we have enough points for a valid polygon
                if len(cleaned_points) >= 3:
                    draw.polygon(cleaned_points, outline=(0, 112, 184), fill=(0, 132, 204))
                else:
                    draw.line(points, fill=(0, 112, 184), width=2)
            else:
                # Not enough points for a polygon, draw lines instead
                draw.line(points, fill=(0, 112, 184), width=2)
        except Exception as e:
            print(f"Error drawing water: {str(e)}")
            try:
                draw.line(points, fill=(0, 112, 184), width=2)
            except:
                pass
    
    # 4. Waterways (rivers, streams)
    for element in waterway_elements:
        points = [latlon_to_pixel(point['lat'], point['lon']) for point in element['geometry']]
        if len(points) < 2:
            continue
            
        tags = element.get('tags', {})
        waterway_type = tags.get('waterway', '')
        
        # Choose width based on waterway type
        if waterway_type in ['river']:
            width = 3
        elif waterway_type in ['stream']:
            width = 2
        else:
            width = 1
        
        # Draw the waterway
        try:
            draw.line(points, fill=(0, 132, 204), width=width)
        except:
            pass
    
    # 5. Other elements
    for element in other_elements:
        points = [latlon_to_pixel(point['lat'], point['lon']) for point in element['geometry']]
        if len(points) < 2:
            continue
            
        # Draw generic element
        try:
            if len(points) > 2:
                draw.polygon(points, outline=(100, 100, 100), fill=None)
            else:
                draw.line(points, fill=(100, 100, 100), width=1)
        except:
            pass
    
    # 6. Roads
    for element in highways:
        points = [latlon_to_pixel(point['lat'], point['lon']) for point in element['geometry']]
        if len(points) < 2:
            continue
            
        tags = element.get('tags', {})
        highway_type = tags.get('highway', '')
        
        # Choose color and width based on road type
        if highway_type in ['motorway', 'trunk', 'primary']:
            color = (255, 69, 0)  # Red-orange
            width = 4
        elif highway_type in ['secondary']:
            color = (255, 165, 0)  # Orange
            width = 3
        elif highway_type in ['tertiary', 'residential']:
            color = (255, 255, 255)  # White
            width = 2
        else:
            color = (220, 220, 220)  # Light gray
            width = 1
        
        # Draw the road
        try:
            draw.line(points, fill=color, width=width)
        except:
            pass
    
    # 7. Buildings
    for element in buildings:
        points = [latlon_to_pixel(point['lat'], point['lon']) for point in element['geometry']]
        if len(points) < 3:
            continue
            
        # Draw the building
        try:
            draw.polygon(points, outline=(90, 90, 90), fill=(169, 169, 169))
        except:
            pass
    
    # Place the marker exactly at the photo coordinates
    photo_pixel = (width // 2, height // 2)
    
    # Draw the marker
    marker_radius = 8
    
    # Draw shadow
    shadow_offset = 2
    draw.ellipse([
        (photo_pixel[0] - marker_radius + shadow_offset, photo_pixel[1] - marker_radius + shadow_offset),
        (photo_pixel[0] + marker_radius + shadow_offset, photo_pixel[1] + marker_radius + shadow_offset)
    ], fill=(50, 50, 50))
    
    # Draw an outer white ring for visibility
    outer_radius = marker_radius + 2
    draw.ellipse([
        (photo_pixel[0] - outer_radius, photo_pixel[1] - outer_radius),
        (photo_pixel[0] + outer_radius, photo_pixel[1] + outer_radius)
    ], fill=None, outline=(255, 255, 255), width=2)
    
    # Draw marker pin
    draw.ellipse([
        (photo_pixel[0] - marker_radius, photo_pixel[1] - marker_radius),
        (photo_pixel[0] + marker_radius, photo_pixel[1] + marker_radius)
    ], fill=(255, 0, 0), outline=(0, 0, 0), width=1)
    
    # Draw white center dot
    draw.ellipse([
        (photo_pixel[0] - 2, photo_pixel[1] - 2),
        (photo_pixel[0] + 2, photo_pixel[1] + 2)
    ], fill=(255, 255, 255))
    
    # Add coordinates text with a background for readability
    try:
        # Try to load a font
        try:
            font = ImageFont.truetype("Arial", 10)
            small_font = ImageFont.truetype("Arial", 8)
        except:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
                small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 8)
            except:
                font = ImageFont.load_default()
                small_font = ImageFont.load_default()
        
        # Add coordinates
        coords_text = f"Lat: {latitude:.6f}, Lon: {longitude:.6f}"
        text_bbox = draw.textbbox((0, 0), coords_text, font=small_font)
        text_width = text_bbox[2] - text_bbox[0]
        
        # Text background
        draw.rectangle([(5, height - 25), (text_width + 15, height - 5)], 
                      fill=(255, 255, 255))
        draw.text((10, height - 20), coords_text, fill=(0, 0, 0), font=small_font)
        
        # Add attribution (required for OpenStreetMap data)
        attribution = "© OpenStreetMap contributors"
        text_bbox = draw.textbbox((0, 0), attribution, font=small_font)
        text_width = text_bbox[2] - text_bbox[0]
        draw.rectangle([(width - text_width - 15, height - 25), (width - 5, height - 5)], 
                      fill=(255, 255, 255))
        draw.text((width - text_width - 10, height - 20), attribution, fill=(0, 0, 0), font=small_font)
    except Exception as e:
        print(f"Error adding text to map: {str(e)}")
    
    # Draw a border around the map
    draw.rectangle([(0, 0), (width-1, height-1)], outline=(180, 180, 180), width=1)
    
    return img

def generate_placeholder_map(latitude, longitude, zoom=14, size=(300, 300)):
    """
    Generate a simplified placeholder map when Overpass API is unavailable.
    Creates visually distinct maps for different coordinates without polygon rendering issues.
    
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
        
        width, height = size
        
        # Use the coordinates to influence the background color for visual distinction
        lat_frac = abs((latitude - int(latitude)) * 100)
        lon_frac = abs((longitude - int(longitude)) * 100)
        
        r = 220 + int(lat_frac * 0.35) % 35  # Range: 220-255
        g = 220 + int(lon_frac * 0.35) % 35  # Range: 220-255
        b = 240  # Keep blue component constant for a blue-ish background
        
        # Create a new image with the generated background color
        img = Image.new('RGB', size, (r, g, b))
        
        # Create a separate canvas for land to avoid polygon issues
        land_canvas = Image.new('RGBA', size, (0, 0, 0, 0))  # Transparent
        land_draw = ImageDraw.Draw(land_canvas)
        
        # Create separate canvas for water too
        water_canvas = Image.new('RGBA', size, (0, 0, 0, 0))  # Transparent
        water_draw = ImageDraw.Draw(water_canvas)
        
        # Generate colors that are influenced by the coordinates
        land_r = 220 + int(lon_frac * 0.3) % 35
        land_g = 220 + int(lat_frac * 0.3) % 35
        land_b = 180 + int((lat_frac + lon_frac) * 0.2) % 40
        land_color = (land_r, land_g, land_b, 230)  # With alpha
        
        water_r = 130 + int(lat_frac * 0.25) % 40
        water_g = 170 + int(lon_frac * 0.25) % 40
        water_b = 210 + int((lat_frac + lon_frac) * 0.15) % 45
        water_color = (water_r, water_g, water_b, 230)  # With alpha
        
        # Use coordinates to create a unique land/water pattern
        land_offset_y = height//2 + int(lat_frac % 20) - 10
        
        # Water takes up the top portion of the map
        water_points = [
            (0, 0),
            (width, 0),
            (width, land_offset_y),
            (0, land_offset_y)
        ]
        water_draw.polygon(water_points, fill=water_color)
        
        # Land creates a uniquely shaped coastline based on coordinates
        land_point1_x = int(lon_frac % 40)
        land_point2_x = width//3 + int(lat_frac % 40) - 20
        land_point3_x = 2*width//3 + int((lat_frac + lon_frac) % 50) - 25
        land_point4_x = width - int(lat_frac % 30)
        
        land_point1_y = land_offset_y + int(lon_frac % 10) - 5
        land_point2_y = land_offset_y + int(lat_frac % 15) - 7
        land_point3_y = land_offset_y + int((lat_frac * lon_frac) % 12) - 6
        land_point4_y = land_offset_y + int((lat_frac + lon_frac) % 20) - 10
        
        land_points = [
            (0, land_point1_y),
            (land_point1_x, land_offset_y),
            (land_point2_x, land_point2_y),
            (land_point3_x, land_point3_y),
            (land_point4_x, land_point4_y),
            (width, land_offset_y),
            (width, height),
            (0, height)
        ]
        land_draw.polygon(land_points, fill=land_color)
        
        # Composite the layers onto the main image
        img = Image.alpha_composite(img.convert('RGBA'), water_canvas)
        img = Image.alpha_composite(img, land_canvas).convert('RGB')
        draw = ImageDraw.Draw(img)
        
        # Draw a grid for reference (no polygon rendering issues with lines)
        grid_color = (max(r-30, 180), max(g-30, 180), max(b-30, 180))
        grid_spacing = min(width, height) // 10
        
        for i in range(0, width, grid_spacing):
            draw.line([(i, 0), (i, height)], fill=grid_color, width=1)
        
        for i in range(0, height, grid_spacing):
            draw.line([(0, i), (width, i)], fill=grid_color, width=1)
        
        # Draw roads (just lines - no polygon rendering issues)
        road_offset_1 = width//4 + int(lat_frac % 40) - 20
        road_offset_2 = height//3 + int(lon_frac % 40) - 20
        
        # Draw main roads with random variation based on coordinates
        draw.line([(road_offset_1, 0), (road_offset_1, height)], fill=(255, 255, 255), width=2)
        draw.line([(0, road_offset_2), (width, road_offset_2)], fill=(255, 255, 255), width=2)
        
        # Draw diagonal road with variation based on coordinates
        draw.line([(width//2 + int(lat_frac % 30) - 15, 0), 
                   (3*width//4 + int(lon_frac % 30) - 15, height)], 
                  fill=(255, 255, 255), width=2)
        
        # Draw secondary road
        secondary_road_y = 2*height//3 + int(lat_frac % 30) - 15
        draw.line([(0, secondary_road_y), (width, secondary_road_y)], 
                 fill=(255, 255, 255), width=1)
        
        # Pin at center of map
        pin_x, pin_y = width // 2, height // 2
        marker_radius = 8
        
        # Draw shadow
        shadow_offset = 2
        draw.ellipse([
            (pin_x - marker_radius + shadow_offset, pin_y - marker_radius + shadow_offset),
            (pin_x + marker_radius + shadow_offset, pin_y + marker_radius + shadow_offset)
        ], fill=(50, 50, 50))
        
        # Draw white outline for visibility
        draw.ellipse([
            (pin_x - marker_radius - 2, pin_y - marker_radius - 2),
            (pin_x + marker_radius + 2, pin_y + marker_radius + 2)
        ], outline=(255, 255, 255), width=2)
        
        # Draw marker
        draw.ellipse([
            (pin_x - marker_radius, pin_y - marker_radius),
            (pin_x + marker_radius, pin_y + marker_radius)
        ], fill=(255, 0, 0), outline=(0, 0, 0), width=1)
        
        # Draw white center
        draw.ellipse([
            (pin_x - 2, pin_y - 2),
            (pin_x + 2, pin_y + 2)
        ], fill=(255, 255, 255))
        
        # Try to load a font
        try:
            try:
                font = ImageFont.truetype("Arial", 10)
                small_font = ImageFont.truetype("Arial", 8)
            except:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
                small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 8)
        except:
            font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Add title indicating this is a placeholder
        title = "Location Map (Placeholder)"
        text_bbox = draw.textbbox((0, 0), title, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        
        # White background for text
        text_bg_padding = 4
        draw.rectangle([
            (width//2 - text_width//2 - text_bg_padding, 5 - text_bg_padding),
            (width//2 + text_width//2 + text_bg_padding, 5 + text_bbox[3] - text_bbox[1] + text_bg_padding)
        ], fill=(255, 255, 255))
        
        # Draw title
        draw.text((width//2 - text_width//2, 5), title, fill=(80, 80, 80), font=font)
        
        # Add coordinates
        coords_text = f"Lat: {latitude:.6f}, Lon: {longitude:.6f}"
        text_bbox = draw.textbbox((0, 0), coords_text, font=small_font)
        text_width = text_bbox[2] - text_bbox[0]
        
        # Background for coordinates
        draw.rectangle([
            (5, height - 25),
            (text_width + 15, height - 5)
        ], fill=(255, 255, 255))
        
        # Draw coordinates
        draw.text((10, height - 20), coords_text, fill=(80, 80, 80), font=small_font)
        
        # Add attribution
        attribution = "© OpenStreetMap contributors"
        text_bbox = draw.textbbox((0, 0), attribution, font=small_font)
        text_width = text_bbox[2] - text_bbox[0]
        
        # Background for attribution
        draw.rectangle([
            (width - text_width - 10, height - 15 - text_bbox[3] + text_bbox[1]),
            (width - 5, height - 5)
        ], fill=(255, 255, 255))
        
        # Draw attribution
        draw.text((width - text_width - 5, height - 15), attribution, fill=(80, 80, 80), font=small_font)
        
        # Border around the map
        draw.rectangle([(0, 0), (width-1, height-1)], outline=(180, 180, 180), width=1)
        
        # Save to temporary file
        temp_img = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        temp_img.close()
        img.save(temp_img.name)
        
        return temp_img.name
        
    except Exception as e:
        print(f"Error generating placeholder map: {str(e)}")
        
        # Last resort fallback - generate a super simple map
        try:
            # Create a very basic map with minimal features
            img = Image.new('RGB', size, (230, 240, 250))
            draw = ImageDraw.Draw(img)
            
            # Draw simple grid
            for i in range(0, size[0], size[0]//10):
                draw.line([(i, 0), (i, size[1])], fill=(200, 200, 200), width=1)
            for i in range(0, size[1], size[1]//10):
                draw.line([(0, i), (size[0], i)], fill=(200, 200, 200), width=1)
            
            # Draw pin
            center = (size[0]//2, size[1]//2)
            radius = 8
            draw.ellipse([
                (center[0]-radius, center[1]-radius),
                (center[0]+radius, center[1]+radius)
            ], fill=(255, 0, 0))
            
            # Add text
            try:
                font = ImageFont.load_default()
                draw.text((10, 10), "Placeholder Map", fill=(0, 0, 0), font=font)
                draw.text((10, size[1]-20), f"Lat: {latitude:.6f}, Lon: {longitude:.6f}", fill=(0, 0, 0), font=font)
            except:
                pass
            
            # Save
            temp_img = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            temp_img.close()
            img.save(temp_img.name)
            return temp_img.name
            
        except:
            # If all else fails, return None
            return None

def generate_map(latitude, longitude, zoom=15, size=(300, 300)):
    """
    Generate a map image with a pin at the specified coordinates using OpenStreetMap data via Overpass API.
    Falls back to a placeholder map if API request fails.
    
    Args:
        latitude (float): Latitude coordinate
        longitude (float): Longitude coordinate
        zoom (int): Zoom level for the map (default: 15)
        size (tuple): Size of the output image (width, height)
        
    Returns:
        str: Path to the generated map image (temporary file)
    """
    try:
        print(f"Generating map for coordinates: Lat {latitude}, Lon {longitude}")
        
        # Validate coordinates
        if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
            print(f"Invalid coordinates: Lat {latitude}, Lon {longitude}")
            return generate_placeholder_map(0, 0, zoom, size)  # Use default coordinates for placeholder
        
        # Calculate radius based on zoom level (higher zoom = smaller radius)
        base_radius = 500  # Moderate radius to get sufficient context
        radius = int(base_radius / (zoom / 10))
        
        # Get map data from Overpass API
        map_data = get_map_data_from_overpass(latitude, longitude, radius)
        
        # Check if we got meaningful data
        if map_data and 'elements' in map_data and len(map_data.get('elements', [])) > 3:
            print(f"Rendering map with {len(map_data.get('elements', []))} elements")
            
            # Render the map
            map_img = render_map_from_overpass_data(map_data, latitude, longitude, size, zoom/10.0)
            
            if map_img:
                # Save to temporary file
                temp_img = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                temp_img.close()
                map_img.save(temp_img.name)
                
                print(f"Successfully generated map: {temp_img.name}")
                return temp_img.name
        else:
            print("Insufficient map data received from Overpass API")
        
        # If we get here, either the API request failed or rendering failed
        print("Falling back to placeholder map")
        return generate_placeholder_map(latitude, longitude, zoom, size)
        
    except Exception as e:
        print(f"Error generating map: {str(e)}")
        print("Falling back to placeholder map due to error")
        return generate_placeholder_map(latitude, longitude, zoom, size)

def generate_compass_indicator(orientation, size=(100, 100)):
    """
    Generate a compass direction indicator showing orientation.
    The orientation value represents the exact direction the camera was facing
    when the photo was taken.
    
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
            try:
                font = ImageFont.truetype("Arial", 12)
            except:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        except IOError:
            font = ImageFont.load_default()
            
        # Draw cardinal direction labels
        for dir_label, angle in [("N", 0), ("NE", 45), ("E", 90), ("SE", 135), 
                              ("S", 180), ("SW", 225), ("W", 270), ("NW", 315)]:
            # Skip intermediate directions for small sizes
            if size[0] < 120 and dir_label in ["NE", "SE", "SW", "NW"]:
                continue
                
            # Calculate position for label
            angle_rad = math.radians(angle)
            label_dist = radius + 5  # A bit outside the circle
            label_x = center_x + label_dist * math.sin(angle_rad)
            label_y = center_y - label_dist * math.cos(angle_rad)
            
            # Get text size for centering
            text_bbox = draw.textbbox((0, 0), dir_label, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            # Draw the label
            draw.text((label_x - text_width/2, label_y - text_height/2), 
                     dir_label, fill=(0, 0, 0), font=font)
        
        # Draw tick marks for each 15 degrees
        for angle in range(0, 360, 15):
            angle_rad = math.radians(angle)
            inner_radius = radius - 3 if angle % 90 == 0 else radius - 2 if angle % 45 == 0 else radius - 1
            outer_radius = radius
            
            start_x = center_x + inner_radius * math.sin(angle_rad)
            start_y = center_y - inner_radius * math.cos(angle_rad)
            end_x = center_x + outer_radius * math.sin(angle_rad)
            end_y = center_y - outer_radius * math.cos(angle_rad)
            
            tick_width = 2 if angle % 90 == 0 else 1
            draw.line([(start_x, start_y), (end_x, end_y)], fill=(0, 0, 0), width=tick_width)
        
        # Convert orientation to radians
        orientation_rad = math.radians(orientation)
        
        # Calculate end point of the arrow
        arrow_length = radius - 5
        end_x = center_x + arrow_length * math.sin(orientation_rad)
        end_y = center_y - arrow_length * math.cos(orientation_rad)
        
        # Draw the direction arrow with shadow for better visibility
        # Shadow
        shadow_offset = 2
        draw.line([(center_x + shadow_offset, center_y + shadow_offset), 
                  (end_x + shadow_offset, end_y + shadow_offset)], 
                 fill=(100, 100, 100), width=3)
        
        # Main arrow
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
        
        # Draw central dot
        draw.ellipse([(center_x - 3, center_y - 3), (center_x + 3, center_y + 3)], 
                    fill=(200, 200, 200), outline=(0, 0, 0))
        
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
