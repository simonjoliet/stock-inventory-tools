import subprocess
import sys
import threading
from datetime import datetime
from os import environ
from pathlib import Path
from queue import Empty, Queue
from shlex import quote
from tkinter import (
    BOTH,
    DISABLED,
    END,
    NORMAL,
    Button,
    Entry,
    Frame,
    Label,
    StringVar,
    Tk,
    filedialog,
    messagebox,
)
from tkinter.scrolledtext import ScrolledText
from tkinter.ttk import Combobox


BASE_DIR = Path(__file__).resolve().parent
DB_DIR = BASE_DIR / "db"
SCRIPT_PYTHON = environ.get("INVENTORY_SCRIPT_PYTHON", sys.executable)

ACTION_GET = "Get inventory"
ACTION_SET = "Set inventory"
PLATFORMS = ("Adobe", "Shutterstock")
GET_SOURCES = ("Live scrape", "HTML file(s)")
SET_SOURCES = ("CSV file", "Single asset")
PAGE_LIMITS = ("All pages", "1", "2", "3", "5", "10", "25", "50", "Custom")


class InventoryGui:
    def __init__(self, root):
        self.root = root
        self.root.title("Stock Inventory Tools")
        self.root.geometry("900x620")
        self.root.minsize(760, 520)

        self.action_var = StringVar(value=ACTION_GET)
        self.platform_var = StringVar(value=PLATFORMS[0])
        self.get_source_var = StringVar(value=GET_SOURCES[0])
        self.set_source_var = StringVar(value=SET_SOURCES[0])
        self.page_limit_var = StringVar(value=PAGE_LIMITS[0])
        self.custom_page_var = StringVar()
        self.get_files_var = StringVar()
        self.set_file_var = StringVar()
        self.asset_var = StringVar()
        self.value_var = StringVar()
        self.command_var = StringVar()
        self.status_var = StringVar(value="Ready")

        self.process = None
        self.events = Queue()

        self.build_ui()
        self.bind_updates()
        self.refresh_state()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def build_ui(self):
        container = Frame(self.root, padx=14, pady=14)
        container.pack(fill=BOTH, expand=True)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(12, weight=1)

        self.action_combo = self.add_combo(
            container, "Action", self.action_var, (ACTION_GET, ACTION_SET), 0
        )
        self.platform_combo = self.add_combo(
            container, "Platform", self.platform_var, PLATFORMS, 1
        )

        self.get_source_combo = self.add_combo(
            container, "Get source", self.get_source_var, GET_SOURCES, 2
        )
        self.page_limit_combo = self.add_combo(
            container, "Page limit", self.page_limit_var, PAGE_LIMITS, 3
        )
        self.custom_page_entry = self.add_entry(
            container, "Custom pages", self.custom_page_var, 4
        )
        self.get_files_entry = self.add_file_row(
            container,
            "HTML files",
            self.get_files_var,
            5,
            self.browse_get_files,
        )

        self.set_source_combo = self.add_combo(
            container, "Set source", self.set_source_var, SET_SOURCES, 6
        )
        self.set_file_entry = self.add_file_row(
            container,
            "CSV file",
            self.set_file_var,
            7,
            self.browse_set_file,
        )
        self.asset_entry = self.add_entry(container, "Asset ID", self.asset_var, 8)
        self.value_entry = self.add_entry(container, "Title/value", self.value_var, 9)

        Label(container, text="Command").grid(row=10, column=0, sticky="w", pady=(10, 2))
        self.command_entry = Entry(
            container, textvariable=self.command_var, state="readonly"
        )
        self.command_entry.grid(row=10, column=1, columnspan=2, sticky="ew", pady=(10, 2))

        controls = Frame(container)
        controls.grid(row=11, column=0, columnspan=3, sticky="ew", pady=(8, 8))
        self.run_button = Button(controls, text="Run", width=14, command=self.run)
        self.run_button.pack(side="left")
        self.clear_button = Button(controls, text="Clear log", command=self.clear_log)
        self.clear_button.pack(side="left", padx=(8, 0))
        Label(controls, textvariable=self.status_var).pack(side="left", padx=(12, 0))

        self.log = ScrolledText(container, height=14, wrap="word")
        self.log.grid(row=12, column=0, columnspan=3, sticky="nsew")

    def add_combo(self, parent, label, variable, values, row):
        Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=3)
        combo = Combobox(
            parent,
            textvariable=variable,
            values=values,
            state="readonly",
            width=24,
        )
        combo.grid(row=row, column=1, columnspan=2, sticky="ew", pady=3)
        return combo

    def add_entry(self, parent, label, variable, row):
        Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=3)
        entry = Entry(parent, textvariable=variable)
        entry.grid(row=row, column=1, columnspan=2, sticky="ew", pady=3)
        return entry

    def add_file_row(self, parent, label, variable, row, browse_command):
        Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=3)
        entry = Entry(parent, textvariable=variable)
        entry.grid(row=row, column=1, sticky="ew", pady=3)
        Button(parent, text="Browse", command=browse_command).grid(
            row=row, column=2, sticky="ew", padx=(8, 0), pady=3
        )
        return entry

    def bind_updates(self):
        for var in (
            self.action_var,
            self.platform_var,
            self.get_source_var,
            self.set_source_var,
            self.page_limit_var,
            self.custom_page_var,
            self.get_files_var,
            self.set_file_var,
            self.asset_var,
            self.value_var,
        ):
            var.trace_add("write", lambda *_: self.refresh_state())

    def browse_get_files(self):
        files = filedialog.askopenfilenames(
            title="Choose HTML files",
            filetypes=(("HTML files", "*.html *.htm"), ("All files", "*.*")),
        )
        if files:
            self.get_files_var.set(";".join(files))

    def browse_set_file(self):
        file_path = filedialog.askopenfilename(
            title="Choose CSV file",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
        )
        if file_path:
            self.set_file_var.set(file_path)

    def refresh_state(self):
        is_get = self.action_var.get() == ACTION_GET
        get_file_mode = self.get_source_var.get() == "HTML file(s)"
        set_file_mode = self.set_source_var.get() == "CSV file"
        custom_pages = self.page_limit_var.get() == "Custom"

        self.set_widget_state(self.get_source_combo, is_get)
        self.set_widget_state(self.page_limit_combo, is_get and not get_file_mode)
        self.set_widget_state(
            self.custom_page_entry, is_get and not get_file_mode and custom_pages
        )
        self.set_widget_state(self.get_files_entry, is_get and get_file_mode)

        self.set_widget_state(self.set_source_combo, not is_get)
        self.set_widget_state(self.set_file_entry, (not is_get) and set_file_mode)
        self.set_widget_state(self.asset_entry, (not is_get) and (not set_file_mode))
        self.set_widget_state(self.value_entry, (not is_get) and (not set_file_mode))

        try:
            command, output_file = self.build_command(validate=False)
            preview = self.format_command(command)
            if output_file is not None:
                preview = f"{preview} > {quote(str(output_file))}"
            self.command_var.set(preview)
        except ValueError:
            self.command_var.set("")

    def set_widget_state(self, widget, enabled):
        widget.configure(state=NORMAL if enabled else DISABLED)
        if isinstance(widget, Combobox):
            widget.configure(state="readonly" if enabled else DISABLED)

    def build_command(self, validate=True):
        platform_arg = "--adobe" if self.platform_var.get() == "Adobe" else "--shutterstock"

        if self.action_var.get() == ACTION_GET:
            command = [SCRIPT_PYTHON, str(BASE_DIR / "get-inventory.py"), platform_arg]

            if self.get_source_var.get() == "HTML file(s)":
                files = self.parse_file_list(self.get_files_var.get())
                if validate and not files:
                    raise ValueError("Choose at least one HTML file.")
                command.extend(["--file", *files])

            if self.get_source_var.get() == "Live scrape":
                page_limit = self.page_limit_var.get()
                if page_limit == "Custom":
                    page_limit = self.custom_page_var.get().strip()
                if page_limit and page_limit != "All pages":
                    if validate and not page_limit.isdigit():
                        raise ValueError("Page limit must be a positive number.")
                    command.extend(["--page", page_limit])

            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            platform_name = self.platform_var.get().lower()
            output_file = DB_DIR / f"{platform_name}-inventory-{timestamp}.csv"
            return command, output_file

        command = [SCRIPT_PYTHON, str(BASE_DIR / "set-inventory.py"), platform_arg]
        if self.set_source_var.get() == "CSV file":
            file_path = self.set_file_var.get().strip()
            if validate and not file_path:
                raise ValueError("Choose a CSV file.")
            command.extend(["--file", file_path])
        else:
            asset_id = self.asset_var.get().strip()
            value = self.value_var.get().strip()
            if validate and not asset_id:
                raise ValueError("Enter an asset ID.")
            if validate and not value:
                raise ValueError("Enter a title/value.")
            command.extend(["--asset", asset_id, "--value", value])
        return command, None

    def parse_file_list(self, value):
        return [part.strip() for part in value.split(";") if part.strip()]

    def format_command(self, command):
        return " ".join(quote(str(part)) for part in command)

    def run(self):
        if self.process is not None:
            messagebox.showinfo("Already running", "Wait for the current job to finish.")
            return

        try:
            command, output_file = self.build_command(validate=True)
        except ValueError as exc:
            messagebox.showerror("Missing option", str(exc))
            return

        self.run_button.configure(state=DISABLED)
        self.status_var.set("Running")
        self.append_log(f"$ {self.format_command(command)}")
        if output_file is not None:
            self.append_log(f"Writing CSV to {output_file}")

        thread = threading.Thread(
            target=self.run_command, args=(command, output_file), daemon=True
        )
        thread.start()
        self.root.after(100, self.drain_events)

    def run_command(self, command, output_file):
        csv_file = None
        try:
            stdout_target = subprocess.PIPE
            stderr_target = subprocess.STDOUT
            if output_file is not None:
                DB_DIR.mkdir(exist_ok=True)
                csv_file = output_file.open("w", encoding="utf-8", newline="")
                stdout_target = csv_file
                stderr_target = subprocess.PIPE

            self.process = subprocess.Popen(
                command,
                cwd=BASE_DIR,
                stdout=stdout_target,
                stderr=stderr_target,
                text=True,
                bufsize=1,
            )

            stream = self.process.stderr if output_file is not None else self.process.stdout
            if stream is not None:
                for line in stream:
                    self.events.put(("log", line.rstrip()))

            return_code = self.process.wait()
            if return_code == 0:
                if output_file is not None:
                    self.events.put(("log", f"Done. CSV saved to {output_file}"))
                else:
                    self.events.put(("log", "Done."))
            else:
                self.events.put(("log", f"Failed with exit code {return_code}."))
        except Exception as exc:
            self.events.put(("error", str(exc)))
        finally:
            if csv_file is not None:
                csv_file.close()
            self.process = None
            self.events.put(("finished", None))

    def drain_events(self):
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "log":
                    self.append_log(payload)
                elif kind == "error":
                    self.append_log(f"Error: {payload}")
                    messagebox.showerror("Error", payload)
                elif kind == "finished":
                    self.status_var.set("Ready")
                    self.run_button.configure(state=NORMAL)
        except Empty:
            pass

        if self.process is not None:
            self.root.after(100, self.drain_events)

    def append_log(self, message):
        self.log.insert(END, f"{message}\n")
        self.log.see(END)

    def clear_log(self):
        self.log.delete("1.0", END)

    def on_close(self):
        if self.process is not None:
            if not messagebox.askyesno(
                "Job running",
                "A job is still running. Stop it and close the GUI?",
            ):
                return
            self.process.terminate()
        self.root.destroy()


def main():
    root = Tk()
    InventoryGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()
