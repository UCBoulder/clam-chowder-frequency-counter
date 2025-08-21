import random
import time
import threading
from pyvisa.errors import VisaIOError

COMMAND_FORMAT = {"input_impedance": ":input{}:impedance {}",
                  "input_coupling": ":input{}:coupling {}",
                  "ref": ":sense:roscillator:source {}",
                  "attenuation": ":input{}:attenuation {}",
                  "lpf": ":input{}:filter:lpass:state {}",
                  "display": ":display:enable {}",
                  "gatetime": ":sense:frequency:arm:stop:timer {}"}

class Counter:
    def __init__(self):
        self.inst = None
        self.data_taking = False
        self.data_buffer = []
        self.lock = threading.Lock()
        self.starttime = None
        self.settings = {"channel": None,
                         "input_impedance": None,
                         "input_coupling": None,
                         "ref": None,
                         "attenuation": None,
                         "lpf": None,
                         "display": None,
                         "gatetime": None}
        #    Key             Values        Type
        #-----------------------------------------
        # channel            1, 2, 3      int
        # input_impedance    50, 1E6      string
        # input_coupling     AC, DC       string
        # ref                INT, EXT     string
        # attenuation        0,1 (on/off) int
        # lpf                0,1          int
        # display            0,1          int
        # gatetime           integer (ms) int

    def start_measurement(self):
        prev_triggertime = time.time() # For deadtime calculation
        self.starttime = time.time()

        while self.data_taking:
            triggertime = time.time()
            deadtime =1000 * (triggertime 
                              - prev_triggertime) - self.settings["gatetime"]
            deadtime = int(deadtime)
            timestamp = triggertime - self.starttime
            prev_triggertime = triggertime # For next loop

            freq = self.take_measurement()

            # Prevent race condition by locking the buffer
            with self.lock:
                self.data_buffer.append((timestamp, freq, deadtime))
        
        # Return to continuous measurement when escaping loop
        self.send_command(":INIT:CONT ON")

    def take_measurement(self):
        self.inst.assert_trigger()
        try:
            freq = float(self.inst.read())
            return freq
        
        except ValueError:
            pass
            
    def initialize(self, channel, set_exp_freq=True):
        """
        Same initialization as Tara's Peasoup program.
        Based on the example from page 3-97 of Agilent 53131A/132A
        programming guide

        Words from Tara:
        Set up counter so it starts immediately on a GPIB trigger
        and stops after a timer given by the gate time.
        Then with *DDT, sets counter up so if it gets hit with a trigger
        the read command is issued (which is an init and a fetch command).
        """
        
        print(f"initializing channel {channel}")
        
        # Reset instrument to factory defaults and clear registers
        self.send_command("*CLS;*RST;*SRE 0;*ESE 0;:STAT:PRES")
        
        # Sets the expected frequency based on the measured frequency
        # Needs to be within 10% at all times
        # Speeds up data acquisition
        try:
            # Set to measure freq on channel x, time arming mode
            # with 1 s gate time
            self.send_command(f":FUNC 'FREQ {channel}';"
                              ":SENS:FREQ:ARM:STAR:SOUR IMM;"
                              ":SENS:FREQ:ARM:STOP:SOUR TIM;"
                              ":SENS:FREQ:ARM:STOP:TIM 1")
            self.inst.timeout = 3000 # 3s timeout
            freqnow = self.send_query(":READ?")
                
            self.send_command(f":FREQ:EXP{channel} {freqnow}")
            self.send_command(f":DIAG:CAL:INT:AUTO OFF;"
                              f":SENS:EVEN{channel}:LEVEL:ABS 0")
            self.send_command("*ESE 1;*SRE 32;*DDT #15READ?")
            
        except VisaIOError:
            print("You forgot to hook up a signal")
            self.inst.clear()

    def apply_settings(self, settings):
        for key, value in settings.items():
            self.apply_setting(key, value)
    
    def apply_setting(self, key, value):
        self.settings[key] = value
        command = self._compose_command(key)
        self.send_command(command)

    def _compose_command(self, key):
        """pattern matching -- requires Python 3.10 or above"""
        channel = self.settings["channel"]
        imp = self.settings["input_impedance"]
        coup = self.settings["input_coupling"]
        ref = self.settings["ref"]
        att = 10 if self.settings["attenuation"] else 1
        lpf = self.settings["lpf"]
        display = self.settings["display"]
        gatetime = self.settings["gatetime"] / 1000
        
        match key:
            case "channel":
                self.initialize(channel)
                imp_coup_att_lpf_gt = \
                    COMMAND_FORMAT["input_impedance"].format(channel, imp)\
                    + ";"\
                    + COMMAND_FORMAT["input_coupling"].format(channel, imp)\
                    + ";"\
                    + COMMAND_FORMAT["attenuation"].format(channel, att)\
                    + ";"\
                    + COMMAND_FORMAT["lpf"].format(channel, lpf)\
                    + ";"\
                    + COMMAND_FORMAT["gatetime"].format(gatetime)
                                    
                return imp_coup_att_lpf_gt
            
            case "input_impedance":
                return COMMAND_FORMAT["input_impedance"].format(channel, imp)
            
            case "input_coupling":
                return COMMAND_FORMAT["input_coupling"].format(channel, coup)
            
            case "ref":
                if ref == "EXT":
                    ext_check = ";:SENS:ROSC:EXT:CHECK ONCE"
                else:
                    ext_check = ""
                return COMMAND_FORMAT["ref"].format(ref) + ext_check
            
            case "attenuation":
                return COMMAND_FORMAT["attenuation"].format(channel, att)
            
            case "lpf":
                return COMMAND_FORMAT["lpf"].format(channel, lpf)
            
            case "display":
                return COMMAND_FORMAT["display"].format(display)
            
            case "gatetime":
                self.inst.timeout = 10 * gatetime * 1000 # ms timeout value
                print(f"Setting timeout to {self.inst.timeout} ms")
                return COMMAND_FORMAT["gatetime"].format(gatetime)

    def send_command(self, command):
        print(f"Sending command: {command}")
        self.inst.write(command)

    def send_query(self, command, timeout=None):
        #print(f"Sending query command: {command}")
        response = self.inst.query(command)
        #print(f"Getting response {response}")
        return response

    def is_ext_referenced(self):
        """Returns True if counter is properly referenced"""
        # TODO
        # Need to actually send command to instrument!
        print("reference check performed")
        
        if self.settings["ref"] == "EXT":
            # When counter is not properly externally referenced,
            # a value of 9.91E37 is returned to the query below
            rosc_freq = float(self.inst.query(":SENS:ROSC:EXT:FREQ?"))
            
            return rosc_freq < 10e15
        else:
            return False

    def error_exists(self):
        # TODO
        # Check for :SYST:ERR? and deal with it
        return False
