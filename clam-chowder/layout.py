import tkinter as tk
import os
from tkinter import ttk
from PIL import Image, ImageTk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


class OneLinerMixin:
    """A mixin to simplify widget additions"""
    def add_button(self, master, text, row, column, sticky=None, width=None):
        button = ttk.Button(master, text=text, width=width)
        button.grid(row=row, column=column, padx=5, pady=5, sticky=sticky)
        self.buttons[text] = button

    def add_combobox(self, master, name, row, column, width=20):
        combobox = ttk.Combobox(master,
                                textvariable=tk.StringVar(),
                                width=width)
        combobox.grid(row=row, column=column)
        combobox.state(['readonly'])
        self.comboboxes[name] = combobox

    def add_led(self, master, name, row, column, sticky=None):
        base_path = os.path.dirname(__file__)
        redpath = os.path.join(base_path, "red.jpg")
        greenpath = os.path.join(base_path, "green.jpg")
        red = ImageTk.PhotoImage(Image.open(redpath))
        green = ImageTk.PhotoImage(Image.open(greenpath))
        led = ttk.Label(master,
                        image=(red, 'disabled', red, '!disabled', green),
                        width=2)
        led.state(['disabled'])  # Default value is disabled (red)
        
        # Need to locally "keep" this image in order to avoid garbage collection
        led.green = green
        led.red = red
        led.grid(row=row, column=column, sticky=sticky)
        self.leds[name] = led


class Layout(ttk.Frame, OneLinerMixin):
    """Overall GUI layout"""
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.rowconfigure(1, weight=1)
        self.columnconfigure(1, weight=1)
        self.grid(row=0, column=0, sticky='NSEW')

        self.buttons = {}
        self.radiobuttons = {}
        self.comboboxes = {}
        self.leds = {}
        
        self.settings = {}
        #    Key             Values        Type
        #-----------------------------------------
        # channel            1, 2, 3      tk.IntVar
        # input_impedance    50, 1E6       tk.StringVar
        # input_coupling     AC, DC       tk.StringVar
        # ref                INT, EXT     tk.StringVar
        # attenuation        0,1 (on/off) tk.IntVar
        # lpf                0,1          tk.IntVar
        # display            0,1          tk.IntVar
        # gatetime           integer      tk.IntVar
        
        self.readings = {"frequency": tk.StringVar(value="000 000 000.000 Hz"),
                         "deadtime": tk.StringVar(value="deadtime : 0 ms")}
        
        # Canvas and Axes objects for plotting
        self.canvas = None
        self.ax = None
        
        self.render()

    def render(self):
        self.add_gpib_frame(row=0, column=0)
        self.add_settings_frame(row=1, column=0)
        self.add_figure_frame(row=1, column=1)
        self.add_button_row(row=2, column=0)

        for child in self.winfo_children():
            child.grid_configure(padx=5, pady=5)

    def add_gpib_frame(self, row, column):
        gpib_frame = ttk.Frame(self)
        ttk.Label(gpib_frame, text="Instrument :").grid(row=0, column=0)
        self.add_combobox(gpib_frame, "GPIB", row=0, column=1, width=15)
        self.add_led(gpib_frame, "GPIB", row=0, column=2, sticky='W')
        self.add_button(gpib_frame, "Connect", row=0, column=3)
        self.add_button(gpib_frame, "Refresh", row=0, column=4)
        # self.add_button(gpib_frame, "toggle!", row=1, column=2)
        gpib_frame.grid(row=row, column=column, columnspan=2, sticky='NSEW')

    def add_settings_frame(self, row, column):
        settings_frame = SettingsFrame(master=self)
        settings_frame.grid(row=row, column=column, sticky='NS')
        self.buttons.update(settings_frame.buttons)
        self.settings.update(settings_frame.settings)
        self.leds.update(settings_frame.leds)
        self.radiobuttons.update(settings_frame.radiobuttons)

    def add_figure_frame(self, row, column):
        fig_frame = ttk.Frame(self)
        s = ttk.Style()
        s.configure('Display.TLabel',font=('Helvetica', 20))
        ttk.Label(fig_frame,
                  textvariable=self.readings['frequency'],
                  style='Display.TLabel').grid(row=0, column=0)
        ttk.Label(fig_frame,
                  textvariable=self.readings['deadtime'],
                  width=15).grid(
                      row=0, column=1, sticky='E')
        fig = Figure(tight_layout=True)
        self.ax = fig.add_subplot()
        self.ax.plot([], [])
        self.ax.set_xlabel("Time (s)", fontsize=16)
        self.ax.set_ylabel("Frequency (MHz)", fontsize=16)
        self.canvas = FigureCanvasTkAgg(fig, master=fig_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=1, column=0, columnspan=2, sticky='NSEW')

        fig_frame.grid(row=row, column=column, sticky='NSEW', padx=20, pady=20)
        fig_frame.columnconfigure(0, weight=1)
        fig_frame.rowconfigure(1, weight=1)

    def update_figure(self, xdata, ydata):
        self.ax.clear()
        self.ax.plot(xdata, ydata)
        self.ax.set_xlabel("Time (s)", fontsize=16)
        self.ax.set_ylabel("Frequency (MHz)", fontsize=16)
        self.ax.yaxis.set_major_formatter(lambda freq, pos: f'{freq/1e6:.5f}')
        self.canvas.draw()

    def update_readings(self, frequency, deadtime):
        self.readings["frequency"].set(f"{frequency:,.3f} Hz".replace(',', ' '))
        self.readings["deadtime"].set(f"deadtime : {deadtime} ms")

    def add_button_row(self, row, column):
        buttons_frame = ttk.Frame(self)
        self.add_button(buttons_frame, "Save", row=0, column=0, sticky='W')
        self.add_button(buttons_frame, "Start", row=0, column=2, sticky='E')
        self.add_button(buttons_frame, "Stop", row=0, column=3, sticky='E')

        buttons_frame.grid(row=row, column=column,
                           columnspan=2, sticky='EW')
        buttons_frame.columnconfigure(1, weight=1)


class SettingsFrame(ttk.LabelFrame, OneLinerMixin):
    def __init__(self, **kwargs):
        super().__init__(text='Settings', **kwargs)
        self.buttons = {}
        self.radiobuttons = {}
        self.comboboxes = {}
        self.leds = {}
        self.settings = {"channel": tk.IntVar(value=1),
                         "input_impedance": tk.StringVar(value="1E6"),
                         "input_coupling": tk.StringVar(value="AC"),
                         "ref": tk.StringVar(value="EXT"),
                         "attenuation": tk.IntVar(value=0),
                         "lpf": tk.IntVar(value=0),
                         "display": tk.IntVar(value=1),
                         "gatetime": tk.IntVar(value=1000)}
        
        self.render()

    def render(self):
        self.add_input_channel_selection(row=0, column=0)
        self.add_input_impedance_selection(row=1, column=0)
        self.add_input_coupling_selection(row=2, column=0)
        self.add_ref_oscillator_selection(row=3, column=0)
        self.add_misc_settings(row=4, column=0)
        self.add_display_onoff_selection(row=5, column=0)
        self.add_gatetime_entry(row=6, column=0)

    def add_input_channel_selection(self, row, column):
        input_channel_frame = ttk.Frame(self)
        ttk.Label(input_channel_frame, text="Input Channel").grid(row=0, column=0)
        ch1 = ttk.Radiobutton(input_channel_frame,
                              text="CH1",
                              variable=self.settings["channel"],
                              value=1)
        ch2 = ttk.Radiobutton(input_channel_frame,
                              text="CH2",
                              variable=self.settings["channel"],
                              value=2)
        ch3 = ttk.Radiobutton(input_channel_frame,
                              text="CH3",
                              variable=self.settings["channel"],
                              value=3)
        
        ch1.grid(row=1, column=0)
        ch2.grid(row=2, column=0)
        ch3.grid(row=3, column=0)
        input_channel_frame.grid(row=row, column=column)
        
        self.radiobuttons["ch1"] = ch1
        self.radiobuttons["ch2"] = ch2
        self.radiobuttons["ch3"] = ch3

        
    def add_input_impedance_selection(self, row, column):
        impedance_selection_frame = ttk.Frame(self)
        ttk.Label(impedance_selection_frame, text="Input Impedance").grid(row=0, column=0)
        ttk.Radiobutton(impedance_selection_frame,
                        text="50 Ω",
                        variable=self.settings["input_impedance"],
                        value="50").grid(row=1, column=0)
        ttk.Radiobutton(impedance_selection_frame,
                        text="1 MΩ",
                        variable=self.settings["input_impedance"],
                        value="1E6").grid(row=2, column=0)
        impedance_selection_frame.grid(row=row, column=column)

    def add_input_coupling_selection(self, row, column):
        acdc_frame = ttk.Frame(self)
        ttk.Label(acdc_frame, text="Input Coupling").grid(row=0, column=0)
        ttk.Radiobutton(acdc_frame,
                        text="AC",
                        variable=self.settings["input_coupling"],
                        value="AC").grid(row=1, column=0)
        ttk.Radiobutton(acdc_frame,
                        text="DC",
                        variable=self.settings["input_coupling"],
                        value="DC").grid(row=2, column=0)
        acdc_frame.grid(row=row, column=column)

    def add_ref_oscillator_selection(self, row, column):
        ref_osc_frame = ttk.Frame(self)
        ttk.Label(ref_osc_frame, text="Reference Oscillator").grid(row=0, column=0)
        radiobutton_int = ttk.Radiobutton(ref_osc_frame,
                                          text="Internal",
                                          variable=self.settings["ref"],
                                          value="INT")
        radiobutton_ext = ttk.Radiobutton(ref_osc_frame,
                                          text="External",
                                          variable=self.settings["ref"],
                                          value="EXT")
        radiobutton_int.grid(row=1, column=0)
        radiobutton_ext.grid(row=2, column=0)
        self.add_led(ref_osc_frame, "ref", row=2, column=1, sticky='W')
        ref_osc_frame.grid(row=row, column=column)

        self.radiobuttons["INT"] = radiobutton_int
        self.radiobuttons["EXT"] = radiobutton_ext

    def add_misc_settings(self, row, column):
        misc_frame = ttk.Frame(self)
        ttk.Label(misc_frame, text="10x attenuation : ").grid(row=0, column=0, sticky='E')
        ttk.Checkbutton(misc_frame,
                        variable=self.settings["attenuation"]).grid(row=0, column=1)
        ttk.Label(misc_frame, text="100 kHz LPF : ").grid(row=1, column=0, sticky='E')
        ttk.Checkbutton(misc_frame,
                        variable=self.settings["lpf"]).grid(row=1, column=1)
        misc_frame.grid(row=row, column=column)

    def add_display_onoff_selection(self, row, column):
        display_frame = ttk.Frame(self)
        ttk.Label(display_frame, text="Front Panel Display").grid(row=0, column=0)
        ttk.Radiobutton(display_frame,
                        text="ON",
                        variable=self.settings["display"],
                        value=1).grid(row=1, column=0)
        ttk.Radiobutton(display_frame,
                        text="OFF",
                        variable=self.settings["display"],
                        value=0).grid(row=2, column=0)
        display_frame.grid(row=row, column=column)

    def add_gatetime_entry(self, row, column):
        gatetime_frame = ttk.Frame(self)
        ttk.Label(gatetime_frame,
                  text="Gate Time (ms)"). grid(row=0, column=0, columnspan=2)
        ttk.Entry(gatetime_frame,
                  textvariable=self.settings["gatetime"],
                  width=6,
                  justify=tk.RIGHT).grid(row=1, column=0, sticky='E')
        self.add_button(gatetime_frame, "Set", row=1, column=1, width=3, sticky='W')
        gatetime_frame.grid(row=row, column=column)
