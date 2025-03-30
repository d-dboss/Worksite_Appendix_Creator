"""
Photo Appendix Generator - Document Generation Module
This module handles creating the output document with photos and metadata.
"""
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from photo_processor import cleanup_temp_files

def create_document(photo_data_list, output_path, images_per_page=2):
    """
    Create a Word document with photos and their captions.
    
    Args:
        photo_data_list (list): List of dictionaries containing photo data
        output_path (str): Path to save the output document
        images_per_page (int): Number of images per page (default: 2)
    
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
        
        return True
    
    except Exception as e:
        print(f"Error creating document: {str(e)}")
        # Clean up any temporary files on error
        cleanup_temp_files(photo_data_list)
        return False
