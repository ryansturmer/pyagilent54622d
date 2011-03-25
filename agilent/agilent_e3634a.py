from common import Instrument, format_number as fmt
import serial

def normalize(l, minimum=-1.0, maximum=1.0):
    M,m = float(max(l)),float(min(l))
    input_range = M-m
    target_range = float(maximum-minimum)
    return [((x-m)/input_range)*target_range + minimum for x in l]

class PowerSupply(Instrument): 

    def __init__(self,port="COM1",baud=9600, timeout=5, verbose=False):
        Instrument.__init__(self, port, baud, timeout, verbose, stopbits=serial.STOPBITS_TWO)

    def apply(self, voltage, current):
        self.command("APPL %s,%s" % (voltage, current))

    def __set_voltage(self, voltage):
        self.command("VOLT %s" % fmt(voltage))
    def __get_voltage(self):
        return float(self.query("VOLT?"))
    voltage = property(__get_voltage, __set_voltage)

    def __set_current(self, current):
        self.command("CURR %s" % fmt(current))
    def __get_current(self):
        return float(self.query("CURR?"))
    current = property(__get_current, __set_current)

    def output(self, b):
        if b:
            self.command("OUTPUT ON")
        else:
            self.command("OUTPUT OFF")

    def is_on(self):
        return self.query("OUTP?")

    def __set_message(self, msg):
        msg = str(msg)
        if len(msg) > 12:
            raise ValueError("Message '%s' too long. (12 chars or less)" % msg)
        self.command("DISP:TEXT '%s'" % msg)
    def __get_message(self, msg):
        return self.query("DISP:TEXT?")
    message = property(__get_message, __set_message)
