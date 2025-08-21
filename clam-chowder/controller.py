import tkinter as tk
from tkinter import filedialog
import threading
import pyvisa
from pyvisa.errors import VisaIOError
import time
from counter import Counter
from layout import Layout

class Controller:
    def __init__(self, layout, counter):
        self.layout = layout
        self.counter = counter
        self.bind()
        self.rm = pyvisa.ResourceManager()
        self.refresh()
        self.data = {"time": [], "frequency": [], "deadtime": []}

    def bind(self):
        self.layout.buttons["Connect"].configure(command=self.connect)
        self.layout.buttons["Refresh"].configure(command=self.refresh)
        self.layout.buttons["Start"].configure(command=self.start)
        self.layout.buttons["Start"].state(['disabled'])
        self.layout.buttons["Stop"].configure(command=self.stop)
        self.layout.buttons["Save"].configure(command=self.save)
        self.layout.buttons["Set"].configure(command=self.set_gatetime)
        self.layout.radiobuttons["INT"].configure(command=self.set_ref_oscillator)
        self.layout.radiobuttons["EXT"].configure(command=self.set_ref_oscillator)

    def connect(self):
        gpib = self.layout.comboboxes["GPIB"].get()
        try:
            inst = self.rm.open_resource(gpib)
            self.layout.leds["GPIB"].state(['!disabled'])
            tk.messagebox.showinfo('Response to "*IDN?"', inst.query("*IDN?"))
            self.counter.inst = self.rm.open_resource(gpib)
            #self.counter.initialize(channel=self.layout.settings["channel"].get())
            self.set_gatetime()
            self.update_settings()
            self.layout.buttons["Start"].state(['!disabled'])
            
        except VisaIOError as e:
            self.layout.leds["GPIB"].state(['disabled'])
            tk.messagebox.showwarning("Connection Error", str(e))

    def get_settings(self):
        """
        Returns a dictionary of settings obtained from GUI.
        Gatetime is handled separately.
        """
        return {name: value.get() for name, value in self.layout.settings.items()
                if not name == "gatetime"}
            
    def refresh(self):
        """Refreshes instruments list"""
        gpib_list = self.rm.list_resources()
        self.layout.comboboxes["GPIB"].set("")
        self.layout.comboboxes["GPIB"].configure(values=gpib_list)
        
        self.counter.inst = None
        self.layout.leds["GPIB"].state(['disabled'])
        self.layout.leds["ref"].state(['disabled'])
        self.layout.buttons["Start"].state(['disabled'])

    def start(self):
        """
        Prepare empty space for storing data and start data taking thread
        """
        for radiobutton in self.layout.radiobuttons.values():
            radiobutton.state(['disabled'])
        
        self.layout.buttons["Start"].state(['disabled'])
        self.layout.buttons["Save"].state(['disabled'])
        self.layout.buttons["Set"].state(['disabled'])
        self.data = {"time": [], "frequency": [], "deadtime": []}
        self.counter.data_taking = True
        self.counter.data_buffer = []

        with open("current_data.txt", "w") as backupfile:
            backupfile.write("Time (s)\tFrequency (Hz)\n")
            
        t = threading.Thread(target=self.counter.start_measurement, daemon=True)
        t.start()
        self.layout.master.after(200, self.update)

    def update(self):
        """Fetch data and update GUI"""
        self.fetch_data()
        self.update_gui()
        self.update_settings()
        
        # Schedule another update if counter is still taking data
        if self.counter.data_taking and self.counter.inst is not None:
            self.layout.master.after(200, self.update)

    def update_settings(self):
        """Compare GUI settings and counter settings and update counter settings"""
        gui_settings = self.get_settings()
        counter_settings = self.counter.settings
        changed_settings = {key: gui_settings[key] for key in gui_settings
                            if not gui_settings[key] == counter_settings[key]}
        self.counter.settings.update(changed_settings)
        self.counter.apply_settings(changed_settings)

        if "ref" in changed_settings.keys():
            if self.counter.is_ext_referenced():
                self.layout.leds["ref"].state(["!disabled"])
            else:
                self.layout.leds["ref"].state(["disabled"])


    def fetch_data(self):
        """ Fetch data from Counter object's data buffer and write to backup file """
        if self.counter.data_buffer:
            with self.counter.lock:
                reading, self.counter.data_buffer = self.counter.data_buffer, []
            
            t = [x[0] for x in reading]
            freq = [x[1] for x in reading]
            deadtime = [x[2] for x in reading]
            self.data["time"] += t
            self.data["frequency"] += freq
            self.data["deadtime"] += deadtime
            
            with open("current_data.txt", "a") as backupfile:
                timefreq = zip(t, freq)
                for (tt, ff) in timefreq:
                    backupfile.write(f"{tt}\t{ff}\n")

    def update_gui(self):
        # Update GUI readings with the most recent values
        try:
            last_freq = self.data["frequency"][-1]
            last_deadtime = self.data["deadtime"][-1]
            self.layout.update_readings(last_freq, last_deadtime)
        except IndexError:
            pass # No data available yet

        self.layout.update_figure(self.data["time"], self.data["frequency"])

    def stop(self):
        self.counter.data_taking = False

        if self.counter.inst is not None:
            time.sleep(self.counter.settings["gatetime"]/1000)
            self.layout.buttons["Start"].state(['!disabled'])
            self.layout.buttons["Save"].state(["!disabled"])
            self.layout.buttons["Set"].state(["!disabled"])
            
            for radiobutton in self.layout.radiobuttons.values():
                radiobutton.state(['!disabled'])

    def save(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("text file", ".txt")])
        try:
            with open(filename, 'w') as f:
                f.write("Time (s)\tFrequency (Hz)\n")
                timefreq = zip(self.data["time"], self.data["frequency"])
                for (time, freq) in timefreq:
                    f.write(f"{time}\t{freq}\n")

        except FileNotFoundError:
            pass   # User probably hit the cancel button

    def set_gatetime(self):
        try:
            gatetime = self.layout.settings["gatetime"].get()
            gatetime_test = gatetime>1 and gatetime<=10000

            if gatetime_test and self.counter.inst is not None:
                self.counter.apply_setting("gatetime", gatetime)
            else:
                tk.messagebox.showwarning("Invalid Value",
                                          "Gate time is invalid or"
                                          " the instrument is not connected.")
            
        except Exception:  # Entry was empty
            pass

    def set_ref_oscillator(self):
        ref = self.layout.settings["ref"].get()

        if self.counter.inst is not None:
            self.counter.apply_setting("ref", ref)

            if self.counter.is_ext_referenced():
                self.layout.leds["ref"].state(['!disabled'])
            else:
                self.layout.leds["ref"].state(['disabled'])

