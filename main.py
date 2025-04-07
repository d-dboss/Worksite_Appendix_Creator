"""
Photo Appendix Generator - Main Application Entry Point
This script starts the GUI application.
"""
import tkinter as tk
from app_gui import PhotoAppendixApp

def main():
    """Main entry point for the application."""
    # Create the main application window
    root = tk.Tk()
    root.title("Photo Appendix Generator")
    root.geometry("600x400") # Adjusted default size slightly

    # Create and start the application
    app = PhotoAppendixApp(root)

    # Start the application main loop
    root.mainloop()

if __name__ == "__main__":
    main()