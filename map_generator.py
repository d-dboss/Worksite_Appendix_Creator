"""
Photo Appendix Generator - Placeholder for Map and Direction Generation
This module provides placeholder functionality for the removed mapping features.
"""
import os
import tempfile
from PIL import Image, ImageDraw, ImageFont

def generate_placeholder_info(latitude, longitude, size=(300, 300)):
    """
    Generate a placeholder image with location info.
    
    Args:
        latitude (float): Latitude coordinate
        longitude (float): Longitude coordinate
        size (tuple): Size of the output image (width, height)
        
    Returns:
        str: Path to the generated placeholder image (temporary file)
    """
    try:
        width, height = size
        img = Image.new('RGB', size, (240, 245, 250))
        draw = ImageDraw.Draw(img)
        
        # Draw a border
        draw.rectangle([(0, 0), (width-1, height-1)], outline=(180, 180, 180), width=1)
        
        # Try to load a font
        try:
            try:
                font = ImageFont.truetype("Arial", 12)
                small_font = ImageFont.truetype("Arial", 10)
            except:
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
                    small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
                except:
                    font = ImageFont.load_default()
                    small_font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Add text
        title = "Location Information"
        draw.text((width//2 - 70, height//2 - 30), title, fill=(80, 80, 80), font=font)
        
        # Add coordinates
        coords_text = f"Lat: {latitude:.6f}, Lon: {longitude:.6f}"
        draw.text((width//2 - 100, height//2), coords_text, fill=(80, 80, 80), font=small_font)
        
        # Save to temporary file
        temp_img = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        temp_img.close()
        img.save(temp_img.name)
        
        return temp_img.name
        
    except Exception as e:
        print(f"Error generating placeholder: {str(e)}")
        return None

def generate_map(latitude, longitude, zoom=15, size=(300, 300)):
    """
    Placeholder for the removed map generation function.
    
    Args:
        latitude (float): Latitude coordinate
        longitude (float): Longitude coordinate
        zoom (int): Zoom level (not used)
        size (tuple): Size of the output image
        
    Returns:
        str: Path to the generated placeholder image or None
    """
    return generate_placeholder_info(latitude, longitude, size)

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
        import math
        
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
        
        # Try to load a font
        try:
            try:
                font = ImageFont.truetype("Arial", 12)
            except:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        except IOError:
            font = ImageFont.load_default()
            
        # Draw cardinal direction labels
        for dir_label, angle in [("N", 0), ("E", 90), ("S", 180), ("W", 270)]:
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
        
        # Draw tick marks for each 30 degrees
        for angle in range(0, 360, 30):
            angle_rad = math.radians(angle)
            inner_radius = radius - 3 if angle % 90 == 0 else radius - 2
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
        
        # Main arrow (red)
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
        
        # Add orientation text at the bottom
        orientation_text = f"{orientation:.1f}°"
        text_bbox = draw.textbbox((0, 0), orientation_text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        draw.text((center_x - text_width//2, center_y + radius + 5), 
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
    Clean up temporary files.
    
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
