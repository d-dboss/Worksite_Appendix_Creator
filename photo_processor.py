"""
Photo Appendix Generator - Photo Processing Module
This module handles reading photos and extracting metadata.
"""
import os
import exifread
from PIL import Image, ExifTags # Import ExifTags for orientation handling
import re
import tempfile
import shutil
import subprocess
import json
from datetime import datetime
from fractions import Fraction
import warnings

# Suppress specific warnings from exifread if they become noisy
warnings.filterwarnings("ignore", category=UserWarning, module='exifread')

# Try to import pillow_heif for HEIC support
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIC_SUPPORT = True
    print("pillow-heif found. HEIC support enabled.")
except ImportError:
    HEIC_SUPPORT = False
    print("Warning: pillow-heif not installed. HEIC support may be limited or require conversion.")

# --- ExifTool Functions ---
def find_exiftool():
    """Tries to find the ExifTool executable."""
    if os.name == 'nt': check_cmds = [['where', 'exiftool.exe'], ['where', 'exiftool']]
    else: check_cmds = [['which', 'exiftool']]
    for cmd in check_cmds:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, encoding='utf-8')
            if result.returncode == 0 and result.stdout:
                path = result.stdout.strip().split('\n')[0]
                if os.path.exists(path):
                     print(f"Found ExifTool at: {path}")
                     return path
        except FileNotFoundError: continue
        except Exception as e: print(f"Error checking for ExifTool with '{' '.join(cmd)}': {e}")
    print("Warning: ExifTool not found in standard locations or PATH.")
    return None

EXIFTOOL_PATH = find_exiftool()

def get_metadata_with_exiftool(photo_path):
    """Use ExifTool to extract metadata."""
    global EXIFTOOL_PATH
    if not EXIFTOOL_PATH: return {}
    try:
        cmd = [EXIFTOOL_PATH, '-j', '-n', '-a', '-G1', photo_path]
        try: result = subprocess.run(cmd, capture_output=True, text=True, check=False, encoding='utf-8', errors='replace')
        except UnicodeDecodeError:
             print("ExifTool output decode error (UTF-8), trying default encoding...")
             result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0 and result.stderr and ("Warning:" not in result.stderr or "Error:" in result.stderr):
            print(f"ExifTool potential error (RC: {result.returncode}): {result.stderr.strip()}")
        if result.stdout:
            try:
                metadata_list = json.loads(result.stdout)
                if metadata_list and isinstance(metadata_list, list) and len(metadata_list) > 0:
                    cleaned_metadata = {k: v for k, v in metadata_list[0].items() if not (isinstance(v, str) and v.lower() in ('null', '', 'none'))}
                    return cleaned_metadata
                return {}
            except json.JSONDecodeError as json_err:
                print(f"Error parsing ExifTool JSON for {os.path.basename(photo_path)}: {json_err}")
                return {}
        else: return {}
    except FileNotFoundError:
         print(f"Error: ExifTool command ('{EXIFTOOL_PATH}') not found during execution."); EXIFTOOL_PATH = None; return {}
    except Exception as e: print(f"Error running ExifTool for {os.path.basename(photo_path)}: {str(e)}"); return {}

# --- Metadata Extraction Logic ---

      
def extract_caption(filename, tags=None, exiftool_metadata=None, mdls_metadata=None, aae_data=None):
    """
    Extracts caption/description, prioritizing user-entered description fields.
    """
    print(f"  Extracting caption for: {filename}")
    caption = None

    # --- Priority 1: ExifTool ---
    if exiftool_metadata:
        print(f"    Checking ExifTool metadata...")
        # ***** FIX: Added 'IFD0:ImageDescription' to the primary list *****
        # These are most likely to hold the user-entered description
        primary_description_fields = [
            'IFD0:ImageDescription', # Added based on ExifTool output for your HEIC
            'EXIF:ImageDescription', # Keep checking standard EXIF group too
            'XMP:Description',       # Common XMP equivalent (used by many apps)
            'IPTC:Caption-Abstract', # IPTC standard caption
            'Apple:Description',     # Specific Apple tag if available via ExifTool
            'QuickTime:Description', # Sometimes used in HEIC containers
            'QuickTime:Title'        # Sometimes Title is used for description
        ]
        # Check these primary fields
        for field in primary_description_fields:
            # Case-insensitive check just in case ExifTool's JSON output differs slightly sometimes
            if field.lower() in map(str.lower, exiftool_metadata.keys()) and isinstance(exiftool_metadata[field], str):
                 value = exiftool_metadata[field].strip()
                 print(f"      Checking ExifTool Primary Field '{field}': Found value '{value[:60]}{'...' if len(value)>60 else ''}'")
                 if value:
                     caption = value
                     print(f"      >> SELECTED Caption from ExifTool '{field}'")
                     return caption # Return *immediately* if a primary description is found
            # else: # Optional: Log if field exists but is not string or is empty
            #      if field in exiftool_metadata:
            #           print(f"      Field '{field}' found but not usable string: {type(exiftool_metadata[field])}")


        # If no primary description found, check other related fields (Title, Comment etc.)
        if caption is None:
            print(f"    Primary description fields not found or empty. Checking secondary fields...")
            secondary_related_fields = [
                'XMP:Title',             # Title might be used
                'IPTC:ObjectName',       # IPTC standard title/name
                'XMP:Headline',
                'EXIF:UserComment',      # Handle potential encoding prefix
                'EXIF:XPTitle', 'EXIF:XPComment', 'EXIF:XPSubject',
                'RIFF:UserComment',
                'Comment'
            ]
            for field in secondary_related_fields:
                 # Case-insensitive check
                 field_lower = field.lower()
                 found_key = next((k for k in exiftool_metadata if k.lower() == field_lower), None)

                 if found_key and isinstance(exiftool_metadata[found_key], str):
                    value = exiftool_metadata[found_key].strip()
                    print(f"      Checking ExifTool Secondary Field '{found_key}': Found value '{value[:60]}{'...' if len(value)>60 else ''}'")
                    # Special handling for UserComment encoding prefixes
                    if found_key.upper() == 'EXIF:USERCOMMENT' and '\x00' in value:
                        parts = value.split('\x00')
                        potential_caption = parts[-1].strip()
                        value = potential_caption if potential_caption else (parts[-2].strip() if len(parts) > 1 else "")
                        print(f"        (UserComment processed value: '{value[:60]}{'...' if len(value)>60 else ''}')")

                    if value:
                        caption = value
                        print(f"      >> SELECTED Caption from ExifTool Secondary '{found_key}'")
                        return caption # Return first non-empty secondary field found

    # --- Priority 2: macOS mdls ---
    if mdls_metadata and caption is None:
        print(f"    ExifTool found no caption. Checking mdls metadata...")
        # Prioritize description field in mdls as well
        mdls_fields_priority = ['kMDItemDescription', 'kMDItemTitle', 'kMDItemHeadline', 'kMDItemSubject', 'kMDItemComment']
        for field in mdls_fields_priority:
             if field in mdls_metadata and mdls_metadata[field] and mdls_metadata[field] != "(null)":
                  value = mdls_metadata[field].strip()
                  print(f"      Checking mdls Field '{field}': Found value '{value[:60]}{'...' if len(value)>60 else ''}'")
                  if value:
                      caption = value
                      print(f"      >> SELECTED Caption from mdls '{field}'")
                      return caption

    # --- Priority 3: exifread Tags ---
    if tags and caption is None:
        print(f"    ExifTool/mdls found no caption. Checking exifread tags...")
        # Only check the most direct description tag from exifread's perspective
        tag_name = 'Image ImageDescription'
        if tag_name in tags:
             try:
                 value = str(tags[tag_name]).strip()
                 print(f"      Checking exifread Field '{tag_name}': Found value '{value[:60]}{'...' if len(value)>60 else ''}'")
                 if '\x00' in value: # Clean potential encoding markers/nulls
                     value = value.split('\x00')[-1].strip()
                 if value:
                     caption = value
                     print(f"      >> SELECTED Caption from exifread '{tag_name}'")
                     return caption
             except Exception as e:
                 print(f"      Error processing exifread tag '{tag_name}': {e}")


    # --- Priority 4: Check AAE Sidecar ---
    if aae_data and caption is None:
        print("    ExifTool/mdls/exifread found no caption. Checking AAE sidecar...")
        match_adj = re.search(r'<key>adjustmentDescription</key>\s*<string>([^<]+)</string>', aae_data)
        if match_adj:
            value = match_adj.group(1).strip()
            print(f"      Checking AAE 'adjustmentDescription': Found value '{value[:60]}{'...' if len(value)>60 else ''}'")
            if value:
                caption = value
                print(f"      >> SELECTED Caption from AAE adjustmentDescription")
                return caption
        match_desc = re.search(r'<string name="description">([^<]+)</string>', aae_data)
        if match_desc: # Less likely for main description, but check as fallback
            value = match_desc.group(1).strip()
            print(f"      Checking AAE 'description': Found value '{value[:60]}{'...' if len(value)>60 else ''}'")
            if value:
                 caption = value
                 print(f"      >> SELECTED Caption from AAE description")
                 return caption

    # --- Fallback ---
    if caption is None:
        print(f"    No specific caption metadata found for {filename}.")

    return caption # Return the found caption or None

    


# --- [ convert_gps_to_decimal, extract_gps_data, extract_orientation_data, get_macos_metadata, get_aae_data, apply_exif_orientation remain the same ] ---
def convert_gps_to_decimal(gps_coords, gps_ref):
    """Converts GPS from deg/min/sec or string to decimal."""
    try:
        # Handle numeric list/tuple [deg, min, sec]
        if isinstance(gps_coords, (list, tuple)) and len(gps_coords) == 3:
            degrees = float(gps_coords[0])
            minutes = float(gps_coords[1])
            seconds = float(gps_coords[2])
            decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
        # Handle single numeric value (already decimal or just degrees)
        elif isinstance(gps_coords, (int, float)):
            decimal = float(gps_coords)
        # Handle string format (attempt parsing)
        elif isinstance(gps_coords, str):
             # Clean string - remove deg, ', " symbols and extra whitespace
            cleaned = re.sub(r'[^\d\.\s-]', '', gps_coords).strip()
            parts = cleaned.split()
            if len(parts) == 3: # Assume deg min sec
                degrees = float(parts[0])
                minutes = float(parts[1])
                seconds = float(parts[2])
                decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
            elif len(parts) == 2: # Assume deg min
                 degrees = float(parts[0])
                 minutes = float(parts[1])
                 decimal = degrees + (minutes / 60.0)
            elif len(parts) == 1: # Assume decimal degrees
                 decimal = float(parts[0])
            else: return None
        else: return None

        if gps_ref and isinstance(gps_ref, str) and decimal >= 0:
            ref = gps_ref.upper().strip()
            if ref in ['S', 'W']: decimal = -decimal

        is_latitude = (gps_ref and gps_ref in ['N', 'S']) or abs(decimal) <= 90
        is_longitude = (gps_ref and gps_ref in ['E', 'W']) or abs(decimal) <= 180
        if is_latitude and not (-90 <= decimal <= 90): return None
        if is_longitude and not (-180 <= decimal <= 180): return None
        return decimal
    except Exception as e: print(f"Error converting GPS coordinates ('{gps_coords}', Ref: '{gps_ref}'): {str(e)}"); return None

def extract_gps_data(tags=None, exiftool_metadata=None, mdls_metadata=None, file_path=None):
    """Extracts GPS Lat/Lon, prioritizing ExifTool, then mdls, then exifread."""
    latitude, longitude = None, None
    if exiftool_metadata:
        gps_keys_sets = [
            {'lat': 'EXIF:GPSLatitude', 'lon': 'EXIF:GPSLongitude', 'lat_ref': 'EXIF:GPSLatitudeRef', 'lon_ref': 'EXIF:GPSLongitudeRef'},
            {'lat': 'Composite:GPSLatitude', 'lon': 'Composite:GPSLongitude'},
            {'lat': 'XMP:GPSLatitude', 'lon': 'XMP:GPSLongitude'},
            {'lat': 'GPS:Latitude', 'lon': 'GPS:Longitude', 'lat_ref': 'GPS:LatitudeRef', 'lon_ref': 'GPS:LongitudeRef'}, ]
        for keys in gps_keys_sets:
            lat_val = exiftool_metadata.get(keys['lat']); lon_val = exiftool_metadata.get(keys['lon'])
            if lat_val is not None and lon_val is not None:
                 lat_ref = exiftool_metadata.get(keys.get('lat_ref')); lon_ref = exiftool_metadata.get(keys.get('lon_ref'))
                 latitude = convert_gps_to_decimal(lat_val, lat_ref); longitude = convert_gps_to_decimal(lon_val, lon_ref)
                 if latitude is not None and longitude is not None: return latitude, longitude
                 else: latitude, longitude = None, None
        if 'Composite:GPSPosition' in exiftool_metadata:
             pos_str = exiftool_metadata['Composite:GPSPosition']
             if isinstance(pos_str, str) and ',' in pos_str:
                  try:
                       lat_str, lon_str = pos_str.split(',')
                       lat_cand = convert_gps_to_decimal(lat_str.strip(), None); lon_cand = convert_gps_to_decimal(lon_str.strip(), None)
                       if lat_cand is not None and lon_cand is not None: return lat_cand, lon_cand
                  except Exception as e: print(f"    Error parsing Composite:GPSPosition: {e}")
    if mdls_metadata:
         lat_val = mdls_metadata.get('kMDItemLatitude'); lon_val = mdls_metadata.get('kMDItemLongitude')
         if lat_val is not None and lon_val is not None and lat_val != "(null)" and lon_val != "(null)":
             try:
                  latitude = float(lat_val); longitude = float(lon_val)
                  if -90 <= latitude <= 90 and -180 <= longitude <= 180: return latitude, longitude
                  else: latitude, longitude = None, None
             except (ValueError, TypeError) as e: print(f"    Error converting mdls GPS values: {e} (Lat='{lat_val}', Lon='{lon_val}')")
    if tags:
        try:
            if 'GPS GPSLatitude' in tags and 'GPS GPSLongitude' in tags:
                lat_val = tags['GPS GPSLatitude'].values; lon_val = tags['GPS GPSLongitude'].values
                lat_ref_tag = tags.get('GPS GPSLatitudeRef'); lon_ref_tag = tags.get('GPS GPSLongitudeRef')
                lat_ref = str(lat_ref_tag.values).strip() if lat_ref_tag else 'N'
                lon_ref = str(lon_ref_tag.values).strip() if lon_ref_tag else 'E'
                latitude = convert_gps_to_decimal(lat_val, lat_ref); longitude = convert_gps_to_decimal(lon_val, lon_ref)
                if latitude is not None and longitude is not None: return latitude, longitude
                else: latitude, longitude = None, None
        except Exception as e: print(f"    Error extracting GPS from exifread tags: {str(e)}")
    return None, None

def extract_orientation_data(tags=None, exiftool_metadata=None, mdls_metadata=None):
    """Extracts compass orientation, prioritizing ExifTool."""
    orientation = None
    if exiftool_metadata:
        orientation_fields = [ 'Composite:GPSImgDirection', 'EXIF:GPSImgDirection', 'XMP:GPSImgDirection', 'GPS:ImgDirection',
            'Composite:GPSDestBearing', 'EXIF:GPSDestBearing', 'XMP:GPSDestBearing', 'GPS:GPSDestBearing',
            'QuickTime:CameraAngle', 'Track1:CameraAngle', 'Track2:CameraAngle', ]
        for field in orientation_fields:
            if field in exiftool_metadata and exiftool_metadata[field] is not None:
                try:
                    value_str = str(exiftool_metadata[field])
                    numeric_part = re.match(r"^[+-]?(\d+(\.\d*)?|\.\d+)", value_str)
                    if numeric_part:
                        orientation = float(numeric_part.group(0))
                        if 0 <= orientation <= 360: return orientation
                        else: orientation = None
                except (ValueError, TypeError) as e: print(f"    Error parsing orientation from ExifTool '{field}': {e}"); continue
    if tags:
        orientation_tags = [ 'GPS GPSImgDirection', 'GPS GPSDestBearing' ]
        for tag_name in orientation_tags:
            if tag_name in tags:
                try:
                    value = tags[tag_name].values
                    if isinstance(value, list): value = value[0]
                    orientation = float(value) if isinstance(value, Fraction) else float(value)
                    if 0 <= orientation <= 360: return orientation
                    else: orientation = None
                except (ValueError, TypeError, IndexError, AttributeError) as e: print(f"    Error parsing orientation from exifread tag '{tag_name}': {e}"); continue
    return None

def get_macos_metadata(photo_path):
    """Uses macOS 'mdls' command to get metadata."""
    if not shutil.which('mdls'): return None
    try:
        cmd = ['mdls', '-nullMarker', '(null)', photo_path]
        result = subprocess.run(cmd, capture_output=True, check=False, text=True, encoding='utf-8')
        if result.returncode == 0 and result.stdout:
             mdls_data = {}
             keywords = ['kMDItemDescription', 'kMDItemTitle', 'kMDItemHeadline', 'kMDItemSubject',
                         'kMDItemComment', 'kMDItemLatitude', 'kMDItemLongitude']
             for line in result.stdout.splitlines():
                 parts = line.split(' = ', 1)
                 if len(parts) == 2:
                     key = parts[0].strip()
                     if key in keywords:
                         value = parts[1].strip().strip('"')
                         if value != '(null)': mdls_data[key] = value
             return mdls_data if mdls_data else None
        else: print(f"Error running mdls (Return Code: {result.returncode}): {result.stderr}"); return None
    except Exception as e: print(f"Error getting macOS metadata via mdls: {str(e)}"); return None

def get_aae_data(photo_path):
    """Reads content of .AAE sidecar file if it exists."""
    aae_path = os.path.splitext(photo_path)[0] + '.AAE'
    if os.path.exists(aae_path):
        try:
            with open(aae_path, 'r', encoding='utf-8', errors='ignore') as f: return f.read()
        except Exception as e: print(f"Error reading AAE file '{aae_path}': {str(e)}")
    return None

def apply_exif_orientation(image):
    """Applies the rotation specified in EXIF Orientation tag to the image object."""
    try:
        for orientation_tag in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation_tag] == 'Orientation': break
        else: return image
        exif = image.getexif()
        if exif is None or orientation_tag not in exif: return image
        orientation = exif[orientation_tag]
        rotation_map = { 2: Image.FLIP_LEFT_RIGHT, 3: Image.ROTATE_180, 4: Image.FLIP_TOP_BOTTOM,
                         5: Image.TRANSPOSE, 6: Image.ROTATE_270, 7: Image.TRANSVERSE, 8: Image.ROTATE_90 }
        if orientation in rotation_map:
            return image.transpose(rotation_map[orientation])
        else: return image
    except (AttributeError, KeyError, IndexError, TypeError, SyntaxError) as e: print(f"Could not get or apply EXIF orientation: {e}"); return image


def extract_metadata_from_photo(photo_path):
    """Extract metadata from a single photo using multiple methods."""
    print(f"\n--- Processing: {os.path.basename(photo_path)} ---")
    photo_data = { 'path': photo_path, 'filename': os.path.basename(photo_path), 'caption': None, 'latitude': None, 'longitude': None,
        'orientation': None, 'temp_file': None, 'width': None, 'height': None, 'error': None }
    original_path = photo_path; processing_path = photo_path; is_heic = photo_path.lower().endswith('.heic'); temp_conversion_file = None
    try:
        if is_heic:
            if HEIC_SUPPORT:
                print("  HEIC file detected. Attempting conversion to temporary JPG...")
                try:
                    with Image.open(photo_path) as img:
                         photo_data['width'], photo_data['height'] = img.size
                         temp_fd, temp_path = tempfile.mkstemp(suffix='.jpg'); os.close(temp_fd)
                         img.convert('RGB').save(temp_path, 'JPEG', quality=90)
                         photo_data['temp_file'] = temp_path; temp_conversion_file = temp_path; processing_path = temp_path
                         print(f"  Successfully converted HEIC to temporary JPG: {os.path.basename(temp_path)}")
                except Exception as e:
                    print(f"  ERROR: Failed to open or convert HEIC file '{os.path.basename(photo_path)}': {str(e)}")
                    photo_data['error'] = f"HEIC processing failed: {e}"; processing_path = original_path
            else: print("  HEIC file detected, but pillow-heif not installed."); processing_path = original_path
        if photo_data['width'] is None and os.path.exists(processing_path):
            try:
                with Image.open(processing_path) as img:
                    img_oriented = apply_exif_orientation(img)
                    photo_data['width'], photo_data['height'] = img_oriented.size
                    print(f"  Image Dimensions (oriented): {photo_data['width']}x{photo_data['height']}")
            except Exception as e:
                print(f"  ERROR: Could not open image '{os.path.basename(processing_path)}': {str(e)}")
                if not photo_data['error']: photo_data['error'] = f"Image open failed: {e}"
        exiftool_metadata = get_metadata_with_exiftool(original_path)
        mdls_metadata = get_macos_metadata(original_path) if os.name == 'posix' else None
        aae_data = get_aae_data(original_path)
        exifread_tags = None
        if os.path.exists(processing_path):
            try:
                with open(processing_path, 'rb') as f: exifread_tags = exifread.process_file(f, stop_tag='JPEGThumbnail', details=False)
            except Exception as e: print(f"  Warning: Could not read tags using exifread from '{os.path.basename(processing_path)}': {str(e)}")

        # ***** FIX: Pass filename to extract_caption *****
        photo_data['caption'] = extract_caption(photo_data['filename'], exifread_tags, exiftool_metadata, mdls_metadata, aae_data)

        photo_data['latitude'], photo_data['longitude'] = extract_gps_data(exifread_tags, exiftool_metadata, mdls_metadata, original_path)
        photo_data['orientation'] = extract_orientation_data(exifread_tags, exiftool_metadata, mdls_metadata)
        if photo_data['caption'] is None:
            print("  No specific caption found. Generating fallback caption.")
            filename_no_ext = os.path.splitext(photo_data['filename'])[0]
            clean_name = re.sub(r'^(IMG|DSC|VID|PXL|Screenshot|Screen Shot)[\s_-]*', '', filename_no_ext, flags=re.IGNORECASE)
            clean_name = re.sub(r'[_ -]+', ' ', clean_name).strip()
            datetime_match = re.search(r'(\d{4})(\d{2})(\d{2})[\s_-]*(\d{2})(\d{2})(\d{2})', clean_name)
            if datetime_match:
                 try:
                     dt_groups = datetime_match.groups()
                     dt_obj = datetime(int(dt_groups[0]), int(dt_groups[1]), int(dt_groups[2]), int(dt_groups[3]), int(dt_groups[4]), int(dt_groups[5]))
                     photo_data['caption'] = f"Photo from {dt_obj.strftime('%Y-%m-%d %H:%M')}"
                 except ValueError: photo_data['caption'] = clean_name if clean_name else filename_no_ext
            else: photo_data['caption'] = clean_name if clean_name else filename_no_ext
            print(f"  Using fallback caption: '{photo_data['caption']}'")
    except Exception as e:
        print(f"  FATAL ERROR processing photo '{os.path.basename(photo_path)}': {str(e)}")
        photo_data['error'] = f"Fatal processing error: {e}"; import traceback; traceback.print_exc()
    if temp_conversion_file: photo_data['temp_file'] = temp_conversion_file
    print(f"--- Finished Processing: {photo_data['filename']} ---")
    print(f"  Caption:     '{photo_data.get('caption', 'N/A')}'")
    print(f"  GPS:         Lat={photo_data.get('latitude', 'N/A')}, Lon={photo_data.get('longitude', 'N/A')}")
    print(f"  Orientation: {photo_data.get('orientation', 'N/A')}")
    print(f"  Dimensions:  {photo_data.get('width', 'N/A')}x{photo_data.get('height', 'N/A')}")
    print(f"  Error:       {photo_data.get('error', 'None')}")
    return photo_data

def extract_metadata_from_photos(photo_paths):
    """Extract metadata from multiple photos."""
    photo_data_list = []
    total = len(photo_paths); print(f"\nStarting metadata extraction for {total} photos...")
    for i, photo_path in enumerate(photo_paths):
        photo_data = extract_metadata_from_photo(photo_path)
        photo_data_list.append(photo_data)
    print(f"\nFinished metadata extraction for {total} photos.")
    return photo_data_list

def cleanup_temp_files(photo_data_list):
    """Clean up temporary HEIC conversion files."""
    if not photo_data_list: return
    cleaned_count = 0
    for photo_data in photo_data_list:
        temp_file_path = photo_data.get('temp_file')
        if temp_file_path and os.path.exists(temp_file_path):
            try: os.unlink(temp_file_path); cleaned_count += 1
            except Exception as e: print(f"ERROR: Failed to remove temp conversion file '{temp_file_path}': {str(e)}")
    if cleaned_count > 0: print(f"Cleaned up {cleaned_count} temporary conversion files.")