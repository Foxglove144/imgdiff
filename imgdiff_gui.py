import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
import sys
from PIL import Image, ImageTk
import imgdiff

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    dnd_available = True
except ImportError:
    dnd_available = False

# Fix for PyInstaller --noconsole mode where sys.stderr might be None or lack isatty
# This prevents crashes in imgdiff.Progress which expects sys.stderr.isatty()
if sys.stderr is None or not hasattr(sys.stderr, "isatty"):

    class NullWriter:
        def write(self, *args, **kwargs):
            pass

        def flush(self):
            pass

        def isatty(self):
            return False

    sys.stderr = NullWriter()


class Options:
    """Mock options object to pass to imgdiff functions."""

    def __init__(self):
        self.outfile = None
        self.viewer = "builtin"
        self.grace = 1.0
        self.highlight = False
        self.smart_highlight = True
        self.opacity = 64
        self.timeout = 300.0
        self.diff_threshold = 20
        self.orientation = "auto"
        self.bgcolor = (255, 255, 255, 255)
        self.sepcolor = (204, 204, 204, 255)
        self.spacing = 3
        self.border = 0
        self.resize = True
        self.diff = None


class ImgDiffGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ImgDiff GUI")
        self.root.geometry("800x600")

        # Variables
        self.file1_path = tk.StringVar()
        self.file2_path = tk.StringVar()
        self.preview_imgs = [None, None]
        self.smart_highlight = tk.BooleanVar(value=True)
        self.highlight = tk.BooleanVar(value=False)
        self.resize = tk.BooleanVar(value=True)
        self.save_diff = tk.BooleanVar(value=False)
        self.diff_threshold = tk.IntVar(value=80)
        self.opacity = tk.IntVar(value=64)
        self.orientation = tk.StringVar(value="auto")

        self.create_widgets()

    def create_widgets(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # File Selection
        files_frame = ttk.LabelFrame(main_frame, text="Images", padding="10")
        files_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        files_frame.columnconfigure(0, weight=1)
        files_frame.columnconfigure(1, weight=0)  # For swap button
        files_frame.columnconfigure(2, weight=1)
        files_frame.rowconfigure(0, weight=1)

        # Image 1 Area
        f1 = ttk.Frame(files_frame)
        f1.grid(row=0, column=0, padx=5, sticky="nsew")
        self.lbl_preview1 = ttk.Label(
            f1, text="Drop Image 1 Here", relief="groove", anchor="center"
        )
        self.lbl_preview1.pack(fill=tk.BOTH, expand=True, ipady=10)
        self.lbl_res1 = ttk.Label(f1, text="", anchor="center")
        self.lbl_res1.pack(fill=tk.X, pady=(2, 0))
        self.entry1 = ttk.Entry(f1, textvariable=self.file1_path)
        self.entry1.pack(fill=tk.X, pady=(5, 2))
        ttk.Button(f1, text="Browse...", command=lambda: self.browse_file(1)).pack(
            fill=tk.X
        )

        # Swap button area
        swap_frame = ttk.Frame(files_frame)
        swap_frame.grid(row=0, column=1, sticky="ns")
        ttk.Button(swap_frame, text="↔", command=self.swap_images, width=2).pack(
            expand=True
        )

        # Image 2 Area
        f2 = ttk.Frame(files_frame)
        f2.grid(row=0, column=2, padx=5, sticky="nsew")
        self.lbl_preview2 = ttk.Label(
            f2, text="Drop Image 2 Here", relief="groove", anchor="center"
        )
        self.lbl_preview2.pack(fill=tk.BOTH, expand=True, ipady=10)
        self.lbl_res2 = ttk.Label(f2, text="", anchor="center")
        self.lbl_res2.pack(fill=tk.X, pady=(2, 0))
        self.entry2 = ttk.Entry(f2, textvariable=self.file2_path)
        self.entry2.pack(fill=tk.X, pady=(5, 2))
        ttk.Button(f2, text="Browse...", command=lambda: self.browse_file(2)).pack(
            fill=tk.X
        )

        # Options
        opts_frame = ttk.LabelFrame(main_frame, text="Options", padding="10")
        opts_frame.pack(fill=tk.X, pady=5)
        opts_frame.columnconfigure(1, weight=1)
        opts_frame.columnconfigure(4, weight=1)

        # --- Checkboxes ---
        cb_frame = ttk.Frame(opts_frame)
        cb_frame.grid(row=0, column=0, columnspan=6, sticky=tk.W, pady=(0, 5))
        ttk.Checkbutton(
            cb_frame,
            text="Smart Highlight",
            variable=self.smart_highlight,
            command=self.on_smart_change,
        ).pack(side=tk.LEFT)
        ttk.Checkbutton(
            cb_frame,
            text="Simple Highlight",
            variable=self.highlight,
            command=self.on_simple_change,
        ).pack(side=tk.LEFT, padx=10)
        ttk.Checkbutton(cb_frame, text="Resize (Lanczos)", variable=self.resize).pack(
            side=tk.LEFT, padx=10
        )
        ttk.Checkbutton(cb_frame, text="Save Output", variable=self.save_diff).pack(
            side=tk.LEFT, padx=10
        )

        # --- Sliders ---
        ttk.Label(opts_frame, text="Opacity:").grid(
            row=1, column=0, sticky=tk.W, padx=(0, 5)
        )
        ttk.Scale(
            opts_frame,
            from_=0,
            to=255,
            variable=self.opacity,
            orient=tk.HORIZONTAL,
            command=self.on_opacity_change,
        ).grid(row=1, column=1, sticky="ew")
        self.opacity_val_label = ttk.Label(opts_frame, text=self.opacity.get(), width=4)
        self.opacity_val_label.grid(row=1, column=2, padx=(5, 10))
        ttk.Label(opts_frame, text="Diff Threshold:").grid(
            row=1, column=3, sticky=tk.W, padx=(0, 5)
        )
        ttk.Scale(
            opts_frame,
            from_=0,
            to=255,
            variable=self.diff_threshold,
            orient=tk.HORIZONTAL,
            command=self.on_threshold_change,
        ).grid(row=1, column=4, sticky="ew")
        self.threshold_val_label = ttk.Label(
            opts_frame, text=self.diff_threshold.get(), width=4
        )
        self.threshold_val_label.grid(row=1, column=5, padx=(5, 0))

        # --- Orientation ---
        ttk.Label(opts_frame, text="Orientation:").grid(
            row=2, column=0, sticky=tk.W, pady=(5, 0)
        )
        orient_frame = ttk.Frame(opts_frame)
        orient_frame.grid(row=2, column=1, columnspan=5, sticky=tk.W, pady=(5, 0))
        ttk.Radiobutton(
            orient_frame, text="Auto", variable=self.orientation, value="auto"
        ).pack(side=tk.LEFT)
        ttk.Radiobutton(
            orient_frame, text="Left-Right", variable=self.orientation, value="lr"
        ).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(
            orient_frame, text="Top-Bottom", variable=self.orientation, value="tb"
        ).pack(side=tk.LEFT)

        # Buttons and Status
        btn_frame = ttk.Frame(main_frame, padding="10")
        btn_frame.pack(fill=tk.X, pady=5)

        self.compare_btn = ttk.Button(
            btn_frame, text="Compare", command=self.run_compare
        )
        self.compare_btn.pack(side=tk.LEFT)

        self.cancel_btn = ttk.Button(
            btn_frame, text="Cancel", command=self.cancel_compare
        )
        self.cancel_btn.pack(side=tk.LEFT, padx=(5, 0))
        self.cancel_btn.state(["disabled"])

        clear_btn = ttk.Button(btn_frame, text="Clear", command=self.clear_images)
        clear_btn.pack(side=tk.LEFT, padx=(5, 0))

        self.status_label = ttk.Label(btn_frame, text="Ready")
        self.status_label.pack(side=tk.LEFT, padx=10)

        self.progress = ttk.Progressbar(main_frame, mode="indeterminate")
        self.progress.pack(fill=tk.X, pady=(0, 5))

        if dnd_available:
            self.setup_dnd()

    def browse_file(self, target):
        filename = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.tiff")],
        )
        if filename:
            self.set_file(target, filename)

    def set_file(self, target, filename):
        if target == 1:
            self.file1_path.set(filename)
            self.update_preview(1, filename)
        else:
            self.file2_path.set(filename)
            self.update_preview(2, filename)

    def update_preview(self, target, filename):
        try:
            img = Image.open(filename)
            width, height = img.size
            resolution = f"{width} x {height}"
            img.thumbnail((350, 350))
            tk_img = ImageTk.PhotoImage(img)
            if target == 1:
                self.lbl_preview1.configure(image=tk_img, text="")
                self.preview_imgs[0] = tk_img
                self.lbl_res1.config(text=resolution)
            else:
                self.lbl_preview2.configure(image=tk_img, text="")
                self.preview_imgs[1] = tk_img
                self.lbl_res2.config(text=resolution)
        except Exception:
            if target == 1:
                self.lbl_preview1.config(image="", text="Drop Image 1 Here")
                self.preview_imgs[0] = None
                self.lbl_res1.config(text="")
            else:
                self.lbl_preview2.config(image="", text="Drop Image 2 Here")
                self.preview_imgs[1] = None
                self.lbl_res2.config(text="")

    def setup_dnd(self):
        for widget, target in [
            (self.lbl_preview1, 1),
            (self.entry1, 1),
            (self.lbl_preview2, 2),
            (self.entry2, 2),
        ]:
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", lambda e, t=target: self.on_drop(e, t))

    def parse_drop_files(self, data):
        # Use tk splitlist to handle Tcl list formatting (braces for spaces)
        return self.root.tk.splitlist(data)

    def on_drop(self, event, target):
        files = self.parse_drop_files(event.data)
        if files:
            self.set_file(target, files[0])
            if len(files) > 1:
                other = 2 if target == 1 else 1
                self.set_file(other, files[1])

    def swap_images(self):
        """Swaps the two selected images."""
        path1 = self.file1_path.get()
        path2 = self.file2_path.get()
        self.set_file(1, path2)
        self.set_file(2, path1)

    def clear_images(self):
        """Clears both image selections and previews."""
        self.set_file(1, "")
        self.set_file(2, "")

    def on_smart_change(self):
        if self.smart_highlight.get():
            self.highlight.set(False)

    def on_simple_change(self):
        if self.highlight.get():
            self.smart_highlight.set(False)

    def on_opacity_change(self, value):
        val = float(value)
        step = 10
        new_val = round(val / step) * step
        self.opacity.set(int(new_val))
        self.opacity_val_label.config(text=f"{int(new_val)}")

    def on_threshold_change(self, value):
        val = float(value)
        self.threshold_val_label.config(text=f"{int(val)}")

    def run_compare(self):
        f1 = self.file1_path.get()
        f2 = self.file2_path.get()

        if not f1 or not f2:
            messagebox.showwarning("Input Required", "Please select two images.")
            return

        if not os.path.isfile(f1) or not os.path.isfile(f2):
            messagebox.showerror("Error", "One or both files do not exist.")
            return

        self.compare_btn.state(["disabled"])
        self.cancel_btn.state(["!disabled"])
        # create cancel event for long-running operations
        self.cancel_event = threading.Event()
        # set progressbar to determinate to show percent updates
        self.progress.config(mode="determinate", maximum=100)
        self.progress["value"] = 0
        self.status_label.config(text="Processing...")
        # ensure indeterminate animation not running
        try:
            self.progress.stop()
        except Exception:
            pass

        t = threading.Thread(target=self.process_images, args=(f1, f2))
        t.daemon = True
        t.start()

    def process_images(self, f1, f2):
        try:
            opts = Options()
            opts.smart_highlight = self.smart_highlight.get()
            opts.highlight = self.highlight.get()
            opts.opacity = self.opacity.get()
            opts.orientation = self.orientation.get()
            opts.resize = self.resize.get()
            opts.diff_threshold = self.diff_threshold.get()
            # pass cancel event and gui progress callback into imgdiff
            opts.cancel_event = getattr(self, "cancel_event", None)

            def gui_cb(percent):
                # accept either dict {percent,msg} or int percent
                def _update(p):
                    try:
                        if isinstance(p, dict):
                            pct = p.get("percent")
                            msg = p.get("msg")
                            if pct is not None:
                                self.progress.config(value=int(pct))
                            if msg:
                                # show the same terminal message in status label
                                self.status_label.config(text=msg)
                        else:
                            self.progress.config(value=int(p))
                    except Exception:
                        pass

                try:
                    self.root.after(0, lambda: _update(percent))
                except Exception:
                    pass

            opts.gui_progress_callback = gui_cb

            img1 = Image.open(f1).convert("RGB")
            img2 = Image.open(f2).convert("RGB")

            # Resize logic
            if opts.resize and img1.size != img2.size:
                w1, h1 = img1.size
                w2, h2 = img2.size
                if w1 * h1 < w2 * h2:
                    try:
                        resample_filter = Image.Resampling.LANCZOS
                    except AttributeError:
                        resample_filter = Image.LANCZOS
                    img1 = img1.resize((w2, h2), resample=resample_filter)
                else:
                    try:
                        resample_filter = Image.Resampling.LANCZOS
                    except AttributeError:
                        resample_filter = Image.LANCZOS
                    img2 = img2.resize((w1, h1), resample=resample_filter)

            if opts.smart_highlight:
                mask1, mask2, diff = imgdiff.slow_highlight(img1, img2, opts)
            elif opts.highlight:
                mask1, mask2, diff = imgdiff.simple_highlight(img1, img2, opts)
            else:
                mask1 = mask2 = diff = None

            opts.diff = diff
            result_img = imgdiff.tile_images(img1, img2, mask1, mask2, opts)

            status_message = "Done."
            if self.save_diff.get():
                # Create a 'diffs' folder one level above the first image's directory
                img1_dir = os.path.dirname(f1)
                parent_dir = os.path.dirname(img1_dir)
                diffs_folder = os.path.join(parent_dir, "diffs")
                os.makedirs(diffs_folder, exist_ok=True)

                # Smart Difference Naming
                name1, ext1 = os.path.splitext(os.path.basename(f1))
                name2, _ = os.path.splitext(os.path.basename(f2))

                common_prefix = os.path.commonprefix([name1, name2])
                remainder2 = name2[len(common_prefix) :]

                if not remainder2:
                    diff_filename = f"{name1}_diff{ext1}"
                else:
                    diff_filename = f"{name1}_diff_{remainder2}{ext1}"

                outfile = os.path.join(diffs_folder, diff_filename)

                result_img.save(outfile)
                status_message = f"Saved to {outfile}"

            # Show result using default viewer
            result_img.show()

            self.root.after(0, lambda: self.status_label.config(text=status_message))
        except Exception as e:
            # If user cancelled, imgdiff raises Timeout; show friendly message
            if isinstance(e, imgdiff.Timeout):
                self.root.after(0, lambda: self.status_label.config(text="Cancelled"))
            else:
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.root.after(0, lambda: self.status_label.config(text="Error."))
        finally:
            # reset progressbar and buttons
            self.root.after(0, lambda: self.progress.config(mode="indeterminate"))
            self.root.after(0, lambda: self.progress.config(value=0))
            self.root.after(0, lambda: self.cancel_btn.state(["disabled"]))
            self.root.after(0, lambda: self.compare_btn.state(["!disabled"]))

    def cancel_compare(self):
        """Set cancel event to abort long-running highlight operations."""
        if getattr(self, "cancel_event", None) is not None:
            self.cancel_event.set()
            self.status_label.config(text="Cancelling...")
            self.cancel_btn.state(["disabled"])


if __name__ == "__main__":
    if dnd_available:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = ImgDiffGUI(root)
    root.mainloop()
