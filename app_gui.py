"""
Photo Appendix Generator - GUI Implementation
This module contains the main application GUI.
"""
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
from photo_processor import extract_metadata_from_photos, cleanup_temp_files
from document_generator import create_document
from utils import get_image_files

class PhotoAppendixApp:
    def __init__(self, master):
        """Initialize the main application window."""
        self.master = master
        self.photo_files = []
        self.output_path = ""
        
        # Create UI elements
        self.create_widgets()
        
    def create_widgets(self):
        """Create and layout all GUI widgets."""
        # Main frame
        main_frame = ttk.Frame(self.master, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Input section
        input_frame = ttk.LabelFrame(main_frame, text="Input", padding="10")
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.input_label = ttk.Label(input_frame, text="No photos selected")
        self.input_label.pack(side=tk.LEFT, padx=5)
        
        self.select_button = ttk.Button(input_frame, text="Select Photos", command=self.select_photos)
        self.select_button.pack(side=tk.RIGHT, padx=5)
        
        # Options section
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding="10")
        options_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(options_frame, text="Images per page:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        self.images_per_page = tk.IntVar(value=2)
        images_per_page_combo = ttk.Combobox(options_frame, textvariable=self.images_per_page, width=5)
        images_per_page_combo['values'] = (1, 2, 4)
        images_per_page_combo.state(['readonly'])
        images_per_page_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Add manual caption option
        self.use_manual_captions = tk.BooleanVar(value=False)
        manual_caption_check = ttk.Checkbutton(
            options_frame, 
            text="Enter captions manually", 
            variable=self.use_manual_captions
        )
        manual_caption_check.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W)
        
        # Output section
        output_frame = ttk.LabelFrame(main_frame, text="Output", padding="10")
        output_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.output_label = ttk.Label(output_frame, text="No output location selected")
        self.output_label.pack(side=tk.LEFT, padx=5)
        
        self.output_button = ttk.Button(output_frame, text="Select Output", command=self.select_output)
        self.output_button.pack(side=tk.RIGHT, padx=5)
        
        # Generate section
        generate_frame = ttk.Frame(main_frame, padding="10")
        generate_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.generate_button = ttk.Button(generate_frame, text="Generate Document", command=self.generate_document)
        self.generate_button.pack(side=tk.RIGHT, padx=5)
        
        # Status section
        status_frame = ttk.Frame(main_frame, padding="10")
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=5)
        
        self.progress = ttk.Progressbar(status_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress.pack(fill=tk.X, side=tk.TOP, padx=5, pady=5)
        
        self.status_label = ttk.Label(status_frame, text="Ready")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
    def select_photos(self):
        """Open file dialog to select photos."""
        filetypes = [
            ("Image files", "*.jpg *.jpeg *.png *.heic"),
            ("JPEG files", "*.jpg *.jpeg"),
            ("PNG files", "*.png"),
            ("HEIC files", "*.heic"),
            ("All files", "*.*")
        ]
        
        # Open file dialog
        files = filedialog.askopenfilenames(
            title="Select Photos",
            filetypes=filetypes
        )
        
        if files:
            self.photo_files = files
            self.input_label.config(text=f"{len(files)} photos selected")
            self.status_label.config(text=f"Selected {len(files)} photos")
        
    def select_output(self):
        """Open file dialog to select output document location."""
        filetypes = [("Word Document", "*.docx"), ("All files", "*.*")]
        
        # Open file dialog
        output_file = filedialog.asksaveasfilename(
            title="Save Document As",
            filetypes=filetypes,
            defaultextension=".docx"
        )
        
        if output_file:
            self.output_path = output_file
            # Display only filename in the label
            filename = os.path.basename(output_file)
            self.output_label.config(text=filename)
            self.status_label.config(text=f"Output will be saved to {filename}")
    
    def generate_document(self):
        """Generate the document with the selected photos."""
        if not self.photo_files:
            messagebox.showerror("Error", "No photos selected. Please select photos first.")
            return
        
        if not self.output_path:
            messagebox.showerror("Error", "No output location selected. Please select an output location first.")
            return
        
        try:
            # Update status
            self.status_label.config(text="Processing photos...")
            self.progress['value'] = 20
            self.master.update_idletasks()
            
            # Extract metadata from photos
            photo_data = extract_metadata_from_photos(self.photo_files)
            
            # If manual captions are enabled, prompt for each photo
            if self.use_manual_captions.get():
                self.status_label.config(text="Enter captions for photos...")
                self.master.update_idletasks()
                
                cancel_caption_entry = False
                
                for i, photo in enumerate(photo_data):
                    if cancel_caption_entry:
                        break
                        
                    filename = photo['filename']
                    default_caption = photo.get('caption', '')
                    
                    # Show a dialog with the filename and ask for caption
                    caption = simpledialog.askstring(
                        "Enter Caption", 
                        f"Caption for {filename} ({i+1} of {len(photo_data)}):\n(Cancel to stop entering captions)",
                        initialvalue=default_caption,
                        parent=self.master
                    )
                    
                    if caption is None:  # User clicked Cancel
                        cancel_caption_entry = True
                    elif caption:  # User entered something
                        photo['caption'] = caption
            
            # Update progress
            self.progress['value'] = 60
            self.status_label.config(text="Generating document...")
            self.master.update_idletasks()
            
            # Create document
            success = create_document(photo_data, self.output_path, images_per_page=self.images_per_page.get())
            
            if success:
                # Complete
                self.progress['value'] = 100
                self.status_label.config(text="Document generated successfully!")
                
                # Show success message
                messagebox.showinfo("Success", f"Document created successfully at:\n{self.output_path}")
            else:
                raise Exception("Failed to create document")
            
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
            self.status_label.config(text="Error generating document")
        finally:
            # Reset progress bar after a delay
            self.master.after(2000, lambda: self.progress.config(value=0))
