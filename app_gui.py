"""
Photo Appendix Generator - GUI Implementation
This module contains the main application GUI.
"""
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
# Note: Removed unused 'get_image_files' import from utils, as selection is direct
from photo_processor import extract_metadata_from_photos, cleanup_temp_files as cleanup_photo_temp_files # Explicit cleanup import
from document_generator import create_document
# map_generator cleanup is handled within document_generator now

class PhotoAppendixApp:
    def __init__(self, master):
        """Initialize the main application window."""
        self.master = master
        master.protocol("WM_DELETE_WINDOW", self.on_closing) # Handle cleanup on close

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
        input_frame = ttk.LabelFrame(main_frame, text="Input Photos", padding="10")
        input_frame.pack(fill=tk.X, padx=5, pady=5)

        self.select_button = ttk.Button(input_frame, text="Select Photos", command=self.select_photos)
        self.select_button.pack(side=tk.LEFT, padx=5, pady=5) # Changed side

        # Use a Listbox to show selected files
        self.photo_listbox = tk.Listbox(input_frame, height=4, width=60)
        self.photo_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        scrollbar = ttk.Scrollbar(input_frame, orient=tk.VERTICAL, command=self.photo_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.photo_listbox.config(yscrollcommand=scrollbar.set)

        # Options section
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding="10")
        options_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(options_frame, text="Images per page:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

        self.images_per_page = tk.IntVar(value=2)
        images_per_page_combo = ttk.Combobox(options_frame, textvariable=self.images_per_page, values=[1, 2, 4], width=5, state='readonly')
        images_per_page_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        # Add include location info option
        self.include_location = tk.BooleanVar(value=True)
        location_check = ttk.Checkbutton(
            options_frame,
            text="Include location map and compass direction (requires GPS/Orientation data in photos)", # Updated text
            variable=self.include_location
        )
        location_check.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W)

        # Add manual caption option
        self.use_manual_captions = tk.BooleanVar(value=False)
        manual_caption_check = ttk.Checkbutton(
            options_frame,
            text="Enter captions manually (overrides photo metadata)", # Updated text
            variable=self.use_manual_captions
        )
        manual_caption_check.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W)

        # Output section
        output_frame = ttk.LabelFrame(main_frame, text="Output Document", padding="10")
        output_frame.pack(fill=tk.X, padx=5, pady=5)

        self.output_button = ttk.Button(output_frame, text="Select Output File", command=self.select_output)
        self.output_button.pack(side=tk.LEFT, padx=5, pady=5) # Changed side

        self.output_label = ttk.Label(output_frame, text="No output file selected", relief=tk.SUNKEN, padding=2, width=50)
        self.output_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)

        # Generate section
        generate_frame = ttk.Frame(main_frame, padding="10")
        generate_frame.pack(fill=tk.X, padx=5, pady=5)

        self.generate_button = ttk.Button(generate_frame, text="Generate Document", command=self.generate_document, style="Accent.TButton") # Added style
        self.generate_button.pack(side=tk.RIGHT, padx=5, pady=5)

        # Style for the generate button
        style = ttk.Style()
        style.configure("Accent.TButton", font=('TkDefaultFont', 10, 'bold'))


        # Status section
        status_frame = ttk.Frame(main_frame, padding="5") # Reduced padding
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=5)

        self.status_label = ttk.Label(status_frame, text="Ready", anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        self.progress = ttk.Progressbar(status_frame, orient=tk.HORIZONTAL, length=150, mode='determinate') # Increased length
        self.progress.pack(side=tk.RIGHT, padx=5) # Moved progress bar right

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
            self.photo_files = list(files) # Ensure it's a list
            # Update listbox
            self.photo_listbox.delete(0, tk.END)
            for file_path in self.photo_files:
                self.photo_listbox.insert(tk.END, os.path.basename(file_path))
            self.status_label.config(text=f"Selected {len(files)} photos")
            # Auto-suggest output filename based on first photo's dir (optional)
            if not self.output_path and self.photo_files:
                 suggested_dir = os.path.dirname(self.photo_files[0])
                 suggested_name = os.path.join(suggested_dir, "Photo_Appendix.docx")
                 self.output_path = suggested_name
                 self.output_label.config(text=os.path.basename(suggested_name))


    def select_output(self):
        """Open file dialog to select output document location."""
        filetypes = [("Word Document", "*.docx"), ("All files", "*.*")]

        # Suggest a filename if one isn't set or exists
        initial_dir = os.path.dirname(self.output_path) if self.output_path else None
        initial_file = os.path.basename(self.output_path) if self.output_path else "Photo_Appendix.docx"

        # Open file dialog
        output_file = filedialog.asksaveasfilename(
            title="Save Document As",
            filetypes=filetypes,
            defaultextension=".docx",
            initialdir=initial_dir,
            initialfile=initial_file
        )

        if output_file:
            self.output_path = output_file
            # Display only filename in the label
            filename = os.path.basename(output_file)
            self.output_label.config(text=filename)
            self.status_label.config(text=f"Output will be saved as {filename}")

    def update_progress(self, value, text):
        """Helper function to update progress bar and status label."""
        self.progress['value'] = value
        self.status_label.config(text=text)
        self.master.update_idletasks() # Force UI update

    def generate_document(self):
        """Generate the document with the selected photos."""
        if not self.photo_files:
            messagebox.showerror("Error", "No photos selected. Please select photos first.")
            return

        if not self.output_path:
            # Prompt to select output if not already selected
            self.select_output()
            if not self.output_path: # Check if selection was cancelled
                 messagebox.showerror("Error", "No output location selected. Please select an output location.")
                 return


        # Disable buttons during generation
        self.generate_button.config(state=tk.DISABLED)
        self.select_button.config(state=tk.DISABLED)
        self.output_button.config(state=tk.DISABLED)

        try:
            # --- Start Processing ---
            self.update_progress(10, "Reading photo metadata...")

            # Extract metadata from photos
            # Pass a callback function for progress updates from photo_processor if needed
            photo_data = extract_metadata_from_photos(self.photo_files)
            self.update_progress(30, "Metadata extracted.")

            # --- Manual Caption Entry (if enabled) ---
            if self.use_manual_captions.get():
                self.update_progress(40, "Waiting for manual captions...")

                cancel_caption_entry = False
                total_photos = len(photo_data)
                for i, photo in enumerate(photo_data):
                    if cancel_caption_entry:
                        break

                    # Update progress within the loop
                    progress_val = 40 + int(20 * (i / total_photos)) # Captions take up 20% of progress
                    self.update_progress(progress_val, f"Enter caption for photo {i+1} of {total_photos}...")

                    filename = photo.get('filename', 'Unknown Photo')
                    default_caption = photo.get('caption', '') # Use extracted caption as default

                    # Show a dialog with the filename and ask for caption
                    caption = simpledialog.askstring(
                        "Enter Caption",
                        f"Caption for: {filename}\n({i+1} of {total_photos})\n\n(Leave blank to keep original/default, Cancel to skip remaining)",
                        initialvalue=default_caption,
                        parent=self.master
                    )

                    if caption is None:  # User clicked Cancel
                        cancel_caption_entry = True
                        self.status_label.config(text="Manual caption entry cancelled.")
                    elif caption is not None:  # User entered something or clicked OK with blank/default
                        photo['caption'] = caption.strip() # Update caption, allow blank

            self.update_progress(60, "Generating document structure...")

            # --- Document Generation ---
            # Create document with location data option
            success = create_document(
                photo_data,
                self.output_path,
                images_per_page=self.images_per_page.get(),
                include_location=self.include_location.get()
                # Pass update_progress callback to create_document if needed for finer steps
            )

            if success:
                self.update_progress(100, "Document generated successfully!")
                messagebox.showinfo("Success", f"Document created successfully:\n{self.output_path}")
            else:
                # Error message handled within create_document, just update status here
                 self.update_progress(0, "Error during document generation. Check console/logs.")
                 messagebox.showerror("Error", "Failed to create the document. Please see console output for details.")


        except Exception as e:
            self.update_progress(0, "An unexpected error occurred.")
            messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}")
            # Consider logging the full traceback here
            import traceback
            print("--- ERROR TRACEBACK ---")
            traceback.print_exc()
            print("-----------------------")
        finally:
            # --- Cleanup and Reset ---
            # Ensure progress bar resets even after error or success
            self.master.after(3000, lambda: self.update_progress(0, "Ready")) # Reset after 3 seconds
            # Re-enable buttons
            self.generate_button.config(state=tk.NORMAL)
            self.select_button.config(state=tk.NORMAL)
            self.output_button.config(state=tk.NORMAL)
            # Photo temp files are cleaned up by document_generator's finally block now

    def on_closing(self):
        """Handle cleanup when the window is closed."""
        print("Application closing. Performing cleanup...")
        # We rely on document_generator and photo_processor cleanup,
        # but could add extra checks here if needed.
        # For instance, prompt user if generation was interrupted.
        self.master.destroy()