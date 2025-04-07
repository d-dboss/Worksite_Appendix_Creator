"""
Photo Appendix Generator - Utility Functions
This module contains helper functions for the application.
"""
import os

def get_image_files(directory):
    """
    Get all image files in a directory (recursive).

    Args:
        directory (str): Path to the directory.

    Returns:
        list: List of image file paths.
    """
    image_extensions = ['.jpg', '.jpeg', '.png', '.heic', '.tif', '.tiff', '.bmp', '.gif'] # Added more types
    image_files = []

    if not os.path.isdir(directory):
         print(f"Error: Provided path '{directory}' is not a valid directory.")
         return []

    print(f"Scanning directory '{directory}' for image files...")
    try:
        # Walk through the directory and subdirectories
        for root, _, files in os.walk(directory):
            for file in files:
                # Check if the file has an image extension (case-insensitive)
                file_lower = file.lower()
                if any(file_lower.endswith(ext) for ext in image_extensions):
                    # Construct full path and add to list
                    full_path = os.path.join(root, file)
                    image_files.append(full_path)

        print(f"Found {len(image_files)} image file(s).")
        return image_files

    except Exception as e:
         print(f"Error scanning directory '{directory}': {e}")
         return []

# Example Usage (can be run directly for testing):
if __name__ == "__main__":
     test_dir = input("Enter directory path to scan for images: ")
     if test_dir:
          files_found = get_image_files(test_dir)
          if files_found:
               print("\nFiles found:")
               for f in files_found:
                    print(f"- {f}")
          else:
               print("No image files found in the specified directory.")