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

def build_overpass_query(latitude, longitude, radius=300):
    """
    Build an Overpass API query to get map features around a location.
    Enhanced to get better terrain outlines and natural features.
    Uses a larger radius for remote locations.
    
    Args:
        latitude (float): Latitude coordinate
        longitude (float): Longitude coordinate
        radius (int): Radius in meters around the point
        
    Returns:
        str: Overpass QL query
    """
    # Create a query with enhanced natural features for better terrain visualization
    # Using a larger radius and more detailed feature types for remote areas
    query = f"""
    [out:json][timeout:45];
    (
      way(around:{radius},{latitude},{longitude})[highway];
      way(around:{radius},{latitude},{longitude})[building];
      way(around:{radius},{latitude},{longitude})[natural];
      way(around:{radius},{latitude},{longitude})[water];
      way(around:{radius},{latitude},{longitude})[waterway];
      way(around:{radius},{latitude},{longitude})[landuse];
      way(around:{radius},{latitude},{longitude})[leisure];
      way(around:{radius},{latitude},{longitude})[amenity];
      way(around:{radius},{latitude},{longitude})[contour];
      way(around:{radius},{latitude},{longitude})[barrier];
      way(around:{radius},{latitude},{longitude})[man_made];
      way(around:{radius},{latitude},{longitude})[mountain_pass];
      way(around:{radius},{latitude},{longitude})[coastline];
      way(around:{radius},{latitude},{longitude})[glacier];
      way(around:{radius},{latitude},{longitude})[ridge];
      way(around:{radius},{latitude},{longitude})[valley];
      rel(around:{radius},{latitude},{longitude})[natural];
      rel(around:{radius},{latitude},{longitude})[water];
      rel(around:{radius},{latitude},{longitude})[landuse];
      node(around:{radius},{latitude},{longitude})[natural=peak];
      node(around:{radius},{latitude},{longitude})[natural];
      node(around:{radius},{latitude},{longitude})[place];
      node(around:{radius},{latitude},{longitude})[amenity];
    );
    out body geom;
    """
    return query

def get_map_data_from_overpass(latitude, longitude, radius=300):
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
        
        # Get an available endpoint - try endpoints in a specific order
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
                    timeout=30
                )
                
                if response.status_code == 200:
                    print(f"Successfully connected to {endpoint}")
                    break
            except Exception as e:
                print(f"Error with endpoint {endpoint}: {str(e)}")
                continue
        
        # Check if we got a successful response
        if response and response.status_code == 200:
            try:
                data = response.json()
                print(f"Successfully retrieved data with {len(data.get('elements', []))} elements")
                return data
            except Exception as e:
                print(f"Error parsing JSON response: {str(e)}")
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
    Simplified for better rendering of map lines and features.
    
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
    
    # Draw a subtle grid
    grid_color = (230, 230, 230)
    for i in range(0, width, width//10):
        draw.line([(i, 0), (i, height)], fill=grid_color, width=1)
    
    for i in range(0, height, height//10):
        draw.line([(0, i), (width, i)], fill=grid_color, width=1)
    
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
    
    # Render different elements in a simplified way
    
    # 1. First render areas (landuse, water bodies)
    for element in data.get('elements', []):
        if element['type'] != 'way' or 'geometry' not in element or len(element['geometry']) < 3:
            continue
            
        tags = element.get('tags', {})
        
        # Skip non-area objects for this pass
        if not (tags.get('landuse') or tags.get('natural') or tags.get('water')):
            continue
        
        points = [latlon_to_pixel(point['lat'], point['lon']) for point in element['geometry']]
        
        # Choose fill color based on tags
        fill_color = None
        if tags.get('water') or tags.get('natural') == 'water':
            fill_color = colors['water']
        elif tags.get('natural') == 'forest' or tags.get('landuse') == 'forest':
            fill_color = colors['forest']
        elif tags.get('landuse') == 'residential':
            fill_color = colors['residential']
        elif tags.get('natural'):
            fill_color = colors['natural']
        
        if fill_color and len(points) >= 3:
            try:
                draw.polygon(points, fill=fill_color, outline=None)
            except Exception as e:
                # Fallback to simpler shapes if polygon fails
                pass
    
    # 2. Then draw waterways
    for element in data.get('elements', []):
        if element['type'] != 'way' or 'geometry' not in element or len(element['geometry']) < 2:
            continue
            
        tags = element.get('tags', {})
        if not tags.get('waterway'):
            continue
            
        points = [latlon_to_pixel(point['lat'], point['lon']) for point in element['geometry']]
        
        try:
            # Draw waterway with thickness based on type
            width = 3 if tags.get('waterway') == 'river' else 2
            draw.line(points, fill=colors['waterway'], width=width)
        except Exception as e:
            pass
    
    # 3. Draw all highways
    for element in data.get('elements', []):
        if element['type'] != 'way' or 'geometry' not in element:
            continue
            
        tags = element.get('tags', {})
        highway_type = tags.get('highway')
        
        if not highway_type:
            continue
            
        points = [latlon_to_pixel(point['lat'], point['lon']) for point in element['geometry']]
        
        if len(points) < 2:
            continue
            
        # Select color and width based on highway type
        color = colors['highway'].get(highway_type, colors['highway']['default'])
        
        # Set line width based on road importance
        if highway_type in ['motorway', 'trunk', 'primary']:
            width = 4
        elif highway_type in ['secondary']:
            width = 3
        elif highway_type in ['tertiary', 'residential']:
            width = 2
        else:
            width = 1
        
        try:
            draw.line(points, fill=color, width=width)
        except Exception as e:
            pass
    
    # 4. Draw buildings
    for element in data.get('elements', []):
        if element['type'] != 'way' or 'geometry' not in element:
            continue
            
        tags = element.get('tags', {})
        if not tags.get('building'):
            continue
            
        points = [latlon_to_pixel(point['lat'], point['lon']) for point in element['geometry']]
        
        if len(points) < 3:
            continue
            
        try:
            draw.polygon(points, fill=colors['building'], outline=(120, 120, 120))
        except Exception as e:
            pass
    
    # Function to convert lat/lon to pixel coordinates
    def latlon_to_pixel(lat, lon):
        x = int((lon - min_lon) / (max_lon - min_lon) * width)
        y = int((max_lat - lat) / (max_lat - min_lat) * height)
        return (x, y)
    
    # Draw a subtle grid for reference
    grid_color = (220, 220, 220)
    for i in range(0, width, width//10):
        draw.line([(i, 0), (i, height)], fill=grid_color, width=1)
    
    for i in range(0, height, height//10):
        draw.line([(0, i), (width, i)], fill=grid_color, width=1)
    
    # Process elements by type for layered rendering (background first, then details)
    # First, separate elements by type for proper layering
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
            fill = (34, 139, 34, 150)  # Semi-transparent green
        elif landuse_type in ['residential', 'commercial']:
            color = (245, 222, 179)  # Tan
            fill = (245, 222, 179, 150)  # Semi-transparent tan
        elif landuse_type in ['farmland', 'farm', 'meadow']:
            color = (173, 209, 158)  # Light green
            fill = (173, 209, 158, 150)  # Semi-transparent light green
        elif landuse_type in ['industrial']:
            color = (209, 198, 207)  # Light purple-gray
            fill = (209, 198, 207, 150)  # Semi-transparent gray
        else:
            color = (200, 200, 200)  # Default gray
            fill = (200, 200, 200, 120)  # Semi-transparent gray
        
        # Draw the polygon
        try:
            draw.polygon(points, outline=color, fill=fill)
        except:
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
            fill = (0, 132, 204, 180)  # Semi-transparent blue
        elif natural_type in ['wood', 'tree', 'forest']:
            color = (12, 128, 44)  # Dark green
            fill = (12, 128, 44, 150)  # Semi-transparent green
        elif natural_type in ['grassland', 'heath']:
            color = (122, 184, 95)  # Light green
            fill = (122, 184, 95, 150)  # Semi-transparent light green
        elif natural_type in ['cliff', 'ridge', 'scree']:
            color = (140, 120, 100)  # Brown
            fill = (140, 120, 100, 150)  # Semi-transparent brown
        else:
            color = (120, 160, 120)  # Default green
            fill = (120, 160, 120, 150)  # Semi-transparent green
        
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
    
    # 3. Water bodies (drawn over natural features)
    for element in water_elements:
        points = [latlon_to_pixel(point['lat'], point['lon']) for point in element['geometry']]
        if len(points) < 3:
            continue
            
        # Draw water body
        try:
            draw.polygon(points, outline=(0, 112, 184), fill=(0, 132, 204, 180))
        except:
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
            
        tags = element.get('tags', {})
        color = (100, 100, 100)  # Default gray
        width = 1
        fill = None
        
        # Draw the element
        if len(points) > 2 and fill:
            try:
                draw.polygon(points, outline=color, fill=fill)
            except:
                try:
                    draw.line(points, fill=color, width=width)
                except:
                    pass
        else:
            try:
                draw.line(points, fill=color, width=width)
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
    
    # 7. Buildings (should be on top of most features)
    for element in buildings:
        points = [latlon_to_pixel(point['lat'], point['lon']) for point in element['geometry']]
        if len(points) < 3:
            continue
            
        # Draw the building
        try:
            draw.polygon(points, outline=(90, 90, 90), fill=(169, 169, 169, 180))
        except:
            pass
    
    # Place the marker exactly at the photo coordinates - use the center of the image
    # This is the most reliable way to ensure the marker is at the correct location
    photo_pixel = (width // 2, height // 2)
    
    # Draw the marker
    marker_radius = 8
    
    # Draw shadow
    shadow_offset = 2
    draw.ellipse([
        (photo_pixel[0] - marker_radius + shadow_offset, photo_pixel[1] - marker_radius + shadow_offset),
        (photo_pixel[0] + marker_radius + shadow_offset, photo_pixel[1] + marker_radius + shadow_offset)
    ], fill=(50, 50, 50, 180))
    
    # Draw an outer white ring for visibility against any background
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
                      fill=(255, 255, 255, 200))
        draw.text((10, height - 20), coords_text, fill=(0, 0, 0), font=small_font)
        
        # Add attribution (required for OpenStreetMap data)
        attribution = "© OpenStreetMap contributors"
        text_bbox = draw.textbbox((0, 0), attribution, font=small_font)
        text_width = text_bbox[2] - text_bbox[0]
        draw.rectangle([(width - text_width - 15, height - 25), (width - 5, height - 5)], 
                      fill=(255, 255, 255, 200))
        draw.text((width - text_width - 10, height - 20), attribution, fill=(0, 0, 0), font=small_font)
    except Exception as e:
        print(f"Error adding text to map: {str(e)}")
    
    # Draw a border around the map
    draw.rectangle([(0, 0), (width-1, height-1)], outline=(180, 180, 180), width=1)
    
    return img
    
    # Add coordinates and attribution
    try:
        # Try to load a font, fall back to default if not available
        try:
            font = ImageFont.truetype("Arial", 10)
            small_font = ImageFont.truetype("Arial", 8)
        except IOError:
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
        draw.rectangle([(5, height - 25), (text_width + 15, height - 5)], fill=(255, 255, 255, 180))
        draw.text((10, height - 20), coords_text, fill=(0, 0, 0), font=small_font)
        
        # Add attribution (required for OpenStreetMap data)
        attribution = "© OpenStreetMap contributors"
        text_bbox = draw.textbbox((0, 0), attribution, font=small_font)
        text_width = text_bbox[2] - text_bbox[0]
        draw.rectangle([(width - text_width - 15, height - 25), (width - 5, height - 5)], fill=(255, 255, 255, 180))
        draw.text((width - text_width - 10, height - 20), attribution, fill=(0, 0, 0), font=small_font)
    except Exception as e:
        print(f"Error adding text to map: {str(e)}")
    
    # Draw a subtle border around the map
    draw.rectangle([(0, 0), (width-1, height-1)], outline=(160, 160, 160), width=1)
    
    return img

def generate_map(latitude, longitude, zoom=15, size=(300, 300)):
    """
    Generate a map image with a pin at the specified coordinates using OpenStreetMap data via Overpass API.
    Simplified to focus on clear visualization with clean lines.
    
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
        
        # Calculate radius based on zoom level (higher zoom = smaller radius)
        base_radius = 500  # Moderate radius to get sufficient context
        radius = int(base_radius / (zoom / 10))
        
        # Get map data from Overpass API
        map_data = get_map_data_from_overpass(latitude, longitude, radius)
        
        # Check if we got meaningful data
        if map_data and 'elements' in map_data and len(map_data.get('elements', [])) > 3:
            # Render the map
            map_img = render_map_from_overpass_data(map_data, latitude, longitude, size, zoom/10.0)
            
            if map_img:
                # Save to temporary file
                temp_img = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                temp_img.close()
                map_img.save(temp_img.name)
                
                print(f"Successfully generated map: {temp_img.name}")
                return temp_img.name
        
        # If we get here, either the API request failed or rendering failed
        print("Using placeholder map instead")
        return generate_placeholder_map(latitude, longitude, zoom, size)
        
    except Exception as e:
        print(f"Error generating map: {str(e)}")
        return generate_placeholder_map(latitude, longitude, zoom, size)
        
        # If we get here, either the API request failed or rendering failed
        print("Falling back to placeholder map")
        return generate_placeholder_map(latitude, longitude, zoom, size)
        
    except Exception as e:
        print(f"Error generating map: {str(e)}")
        return generate_placeholder_map(latitude, longitude, zoom, size)

def generate_placeholder_map(latitude, longitude, zoom=14, size=(300, 300)):
    """
    Generate a simplified placeholder map when Overpass API is unavailable.
    Focused on clarity and clean lines.
    
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
        
        # Create a clean, simple map image
        width, height = size
        img = Image.new('RGB', size, (240, 245, 250))  # Light blue-gray background
        draw = ImageDraw.Draw(img)
        
        # Define colors
        grid_color = (220, 220, 220)   # Light gray for grid
        text_color = (80, 80, 80)      # Dark gray for text
        pin_color = (255, 0, 0)        # Red for pin
        
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
        
        # Draw grid lines
        for i in range(0, width, width//10):
            draw.line([(i, 0), (i, height)], fill=grid_color, width=1)
        
        for i in range(0, height, height//10):
            draw.line([(0, i), (width, i)], fill=grid_color, width=1)
        
        # Simple geography features - for placeholder only
        # Draw simplified land area
        land_color = (245, 245, 235)  # Light tan
        land_shape = [
            (0, height//2), 
            (width//3, height//2-15),
            (2*width//3, height//2-5),
            (width, height//2+10),
            (width, height),
            (0, height)
        ]
        draw.polygon(land_shape, fill=land_color)
        
        # Draw a simple road
        road_color = (255, 255, 255)  # White
        draw.line([(width//4, 0), (width//4, height)], fill=road_color, width=3)
        draw.line([(0, height//2), (width, height//2)], fill=road_color, width=3)
        
        # Pin at center of map
        pin_x, pin_y = width // 2, height // 2
        marker_radius = 8
        
        # White outline for visibility
        draw.ellipse([(pin_x-marker_radius-2, pin_y-marker_radius-2), 
                     (pin_x+marker_radius+2, pin_y+marker_radius+2)], 
                    outline=(255, 255, 255), width=2)
        
        # Shadow
        shadow_offset = 2
        draw.ellipse([(pin_x-marker_radius+shadow_offset, pin_y-marker_radius+shadow_offset), 
                     (pin_x+marker_radius+shadow_offset, pin_y+marker_radius+shadow_offset)], 
                    fill=(50, 50, 50))
        
        # Red marker
        draw.ellipse([(pin_x-marker_radius, pin_y-marker_radius), 
                     (pin_x+marker_radius, pin_y+marker_radius)], 
                    fill=pin_color, outline=(0, 0, 0), width=1)
        
        # White center dot
        draw.ellipse([(pin_x-2, pin_y-2), (pin_x+2, pin_y+2)], 
                    fill=(255, 255, 255))
        
        # Title
        title = "Location Map"
        text_bbox = draw.textbbox((0, 0), title, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        draw.text((width//2 - text_width//2, 5), title, fill=text_color, font=font)
        
        # Coordinates with background for readability
        lat_str = f"Lat: {latitude:.6f}"
        lon_str = f"Lon: {longitude:.6f}"
        
        lat_bbox = draw.textbbox((0, 0), lat_str, font=small_font)
        lat_width = lat_bbox[2] - lat_bbox[0]
        lon_bbox = draw.textbbox((0, 0), lon_str, font=small_font)
        lon_width = lon_bbox[2] - lon_bbox[0]
        
        max_width = max(lat_width, lon_width)
        
        # Background for text
        draw.rectangle([(width//2 - max_width//2 - 5, height-35), 
                       (width//2 + max_width//2 + 5, height-5)], 
                      fill=(255, 255, 255))
        
        # Coordinates text
        draw.text((width//2 - lat_width//2, height-25), lat_str, fill=text_color, font=small_font)
        draw.text((width//2 - lon_width//2, height-15), lon_str, fill=text_color, font=small_font)
        
        # Attribution
        attribution = "© OpenStreetMap contributors"
        text_bbox = draw.textbbox((0, 0), attribution, font=small_font)
        text_width = text_bbox[2] - text_bbox[0]
        draw.rectangle([(width - text_width - 10, 5), (width - 5, 20)], fill=(255, 255, 255))
        draw.text((width - text_width - 5, 8), attribution, fill=text_color, font=small_font)
        
        # Save to temporary file
        temp_img = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        temp_img.close()
        img.save(temp_img.name)
        
        return temp_img.name
        
    except Exception as e:
        print(f"Error generating placeholder map: {str(e)}")
        return None
        
        # Define colors
        water_color = (128, 195, 230)  # Light blue for water
        land_color = (240, 240, 224)   # Light tan for land
        road_color = (255, 255, 255)   # White for roads
        grid_color = (200, 200, 200)   # Light gray for grid
        text_color = (80, 80, 80)      # Dark gray for text
        pin_color = (255, 0, 0)        # Red for pin
        
        # Try to load a font, fall back to default if not available
        try:
            try:
                font = ImageFont.truetype("Arial", 12)
                small_font = ImageFont.truetype("Arial", 8)
            except:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
                small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 8)
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
        
        # Add some terrain features
        # Hills
        hill1_shape = [
            (width//6, height//2),
            (width//4, height//3+15),
            (width//3, height//2-5)
        ]
        hill2_shape = [
            (width//2, height//2+5),
            (2*width//3, height//3+25),
            (3*width//4, height//2+10)
        ]
        draw.polygon(hill1_shape, fill=(220, 220, 204), outline=(200, 200, 180))
        draw.polygon(hill2_shape, fill=(220, 220, 204), outline=(200, 200, 180))
        
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
        
        # Draw contour lines for terrain
        for i in range(1, 5):
            offset = i * 10
            contour_shape = [
                (width//6 + offset, height//2 - offset//2),
                (width//4 + offset//2, height//3 + 15 - offset//3),
                (width//3 + offset, height//2 - 5 - offset//2)
            ]
            draw.line(contour_shape, fill=(180, 180, 160), width=1)
            
            contour_shape2 = [
                (width//2 + offset, height//2 + 5 - offset//2),
                (2*width//3 + offset//2, height//3 + 25 - offset//3),
                (3*width//4 + offset, height//2 + 10 - offset//2)
            ]
            draw.line(contour_shape2, fill=(180, 180, 160), width=1)
        
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
        draw.rectangle([(0, 0), (width-1, height-1)], outline=(180, 180, 180), width=2)
        
        # The pin MUST represent the exact photo location coordinates
        # For placeholder maps, this is always the center of the image
        pin_x, pin_y = width // 2, height // 2
        
        # Draw a nicer pin
        pin_radius = 8
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
        
        # Add background for better readability
        draw.rectangle([(width//2 - max(lat_width, lon_width)//2 - 5, height-35), 
                       (width//2 + max(lat_width, lon_width)//2 + 5, height-5)], 
                      fill=(255, 255, 255, 128))
        
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
