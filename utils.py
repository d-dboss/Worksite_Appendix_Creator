"""
Photo Appendix Generator - Utility Functions
This module contains helper functions for the application.
"""
import os

def get_image_files(directory):
    """
    Get all image files in a directory.
    
    Args:
        directory (str): Path to the directory
        
    Returns:
        list: List of image file paths
    """
    image_extensions = ['.jpg', '.jpeg', '.png', '.heic']
    image_files = []
    
    # Walk through the directory
    for root, _, files in os.walk(directory):
        for file in files:
            # Check if the file has an image extension
            if any(file.lower().endswith(ext) for ext in image_extensions):
                # Add the full path to the list
                image_files.append(os.path.join(root, file))
    
    return image_files
