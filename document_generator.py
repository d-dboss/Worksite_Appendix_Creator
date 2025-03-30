"""
Photo Appendix Generator - Document Generation Module
This module handles creating the output document with photos and metadata.
"""
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from photo_processor import cleanup_temp_files
from map_generator import generate_map, generate_compass_indicator, cleanup_temp_files as cleanup_map_files

def create_document(photo_data_list, output_path, images_per_page=2, include_location=True):
    """
    Create a Word document with photos and their captions.
    
    Args:
        photo_data_list (list): List of dictionaries containing photo data
        output_path (str): Path to save the output document
        images_per_page (int): Number of images per page (default: 2)
        include_location (bool): Whether to include location data (default: True)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create a new document
        doc = Document()
        
        # Set document properties
        doc.core_properties.title = "Photo Appendix"
        doc.core_properties.author = "Photo Appendix Generator"
        
        # Set margins
        for section in doc.sections:
            section.top_margin = Inches(1)
            section.bottom_margin = Inches(1)
            section.left_margin = Inches(1)
            section.right_margin = Inches(1)
        
        # Add title
        title = doc.add_heading("Photo Appendix", level=1)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Add a brief description
        doc.add_paragraph("This document contains photos and their associated metadata.")
        
        # Add a page break before the photos
        doc.add_page_break()
        
        # Calculate image dimensions based on page size and images_per_page
        page_width = Inches(6.5)  # 8.5" - 2" margins
        
        if images_per_page == 1:
            img_width = page_width
        elif images_per_page == 2:
            img_width = page_width
        else:  # 4 images per page
            img_width = page_width / 2
        
        # Calculate smaller sizes for maps and compass indicators
        map_width = Inches(1.5)
        compass_width = Inches(1)
        
        # Keep track of temporary map and compass files for cleanup
        temp_files_to_cleanup = []
        
        # Add photos and captions to the document
        for i, photo_data in enumerate(photo_data_list):
            # Add page break if needed (except for the first image)
            if i > 0 and i % images_per_page == 0:
                doc.add_page_break()
            
            # Add the image - use the temp file if available, otherwise use original path
            image_path = photo_data.get('temp_file', None) or photo_data['path']
            
            try:
                picture = doc.add_picture(image_path, width=img_width)
                
                # Add the caption as a paragraph
                caption = doc.add_paragraph()
                caption_text = caption.add_run(photo_data.get('caption', '') or "No caption available")
                caption_text.font.size = Pt(10)
                caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
                
                # If location data is available and should be included
                if include_location:
                    # Check if GPS data is available
                    has_gps = 'latitude' in photo_data and 'longitude' in photo_data
                    has_orientation = 'orientation' in photo_data
                    
                    if has_gps or has_orientation:
                        # Add a horizontal line
                        doc.add_paragraph("_" * 50)
                        
                        # Create a table for location data (1 row, 2 columns)
                        location_table = doc.add_table(rows=1, cols=2)
                        
                        # Set table width
                        location_table.autofit = False
                        location_table.width = page_width
                        
                        # Add map if GPS coordinates are available
                        if has_gps:
                            latitude = photo_data['latitude']
                            longitude = photo_data['longitude']
                            
                            # Generate map
                            map_path = generate_map(latitude, longitude)
                            
                            if map_path:
                                # Keep track of file for cleanup
                                temp_files_to_cleanup.append(map_path)
                                
                                # Add map to first cell
                                map_cell = location_table.cell(0, 0)
                                map_paragraph = map_cell.paragraphs[0]
                                map_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                                
                                # Add a title for the map
                                map_title = map_paragraph.add_run("Location\n")
                                map_title.bold = True
                                map_title.font.size = Pt(9)
                                
                                # Add the map image
                                map_run = map_paragraph.add_run()
                                map_run.add_picture(map_path, width=map_width)
                                
                                # Add coordinates below the map
                                coords_text = f"\nLat: {latitude:.6f}, Lon: {longitude:.6f}"
                                coords_run = map_paragraph.add_run(coords_text)
                                coords_run.font.size = Pt(8)
                        
                        # Add compass if orientation data is available
                        if has_orientation:
                            orientation = photo_data['orientation']
                            
                            # Generate compass indicator
                            compass_path = generate_compass_indicator(orientation)
                            
                            if compass_path:
                                # Keep track of file for cleanup
                                temp_files_to_cleanup.append(compass_path)
                                
                                # Add compass to second cell
                                compass_cell = location_table.cell(0, 1)
                                compass_paragraph = compass_cell.paragraphs[0]
                                compass_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                                
                                # Add a title for the compass
                                compass_title = compass_paragraph.add_run("Direction\n")
                                compass_title.bold = True
                                compass_title.font.size = Pt(9)
                                
                                # Add the compass image
                                compass_run = compass_paragraph.add_run()
                                compass_run.add_picture(compass_path, width=compass_width)
                                
                                # Add orientation below the compass
                                direction_text = f"\nOrientation: {orientation:.1f}°"
                                direction_run = compass_paragraph.add_run(direction_text)
                                direction_run.font.size = Pt(8)
                
                # Add some space after the caption
                if (i + 1) % images_per_page != 0 and i < len(photo_data_list) - 1:
                    doc.add_paragraph()
                    
            except Exception as e:
                print(f"Error adding image {photo_data['path']}: {str(e)}")
                # Add an error note in the document
                error_para = doc.add_paragraph()
                error_run = error_para.add_run(f"Error adding image: {photo_data['filename']}")
                error_run.font.italic = True
                error_run.font.color.rgb = RGBColor(255, 0, 0)  # Red text
        
        # Save the document
        doc.save(output_path)
        
        # Clean up any temporary files
        cleanup_temp_files(photo_data_list)
        cleanup_map_files(temp_files_to_cleanup)
        
        return True
    
    except Exception as e:
        print(f"Error creating document: {str(e)}")
        # Clean up any temporary files on error
        cleanup_temp_files(photo_data_list)
        cleanup_map_files(temp_files_to_cleanup)
        return False
