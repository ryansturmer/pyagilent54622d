from common import Instrument, format_number as fmt

def normalize(l, minimum=-1.0, maximum=1.0):
    M,m = float(max(l)),float(min(l))
    input_range = M-m
    target_range = float(maximum-minimum)
    return [((x-m)/input_range)*target_range + minimum for x in l]

class FunctionGenerator(Instrument): 

    SIN = 'SIN'
    SQUARE = 'SQU'
    TRIANGLE = 'TRI'
    RAMP = 'RAMP'
    NOISE = 'NOIS'
    DC = 'DC'
    TYPES = (SIN, SQUARE, TRIANGLE, RAMP, NOISE, DC)

    LOAD_50OHMS = '50'
    LOAD_INFINITY = 'INF'
    LOADS = (LOAD_50OHMS, LOAD_INFINITY)

    def __init__(self,port="COM1",baud=57600, timeout=5, verbose=False):
        Instrument.__init__(self, port, baud, timeout, verbose)

    def apply(self, type, freq=None, amp=None, offset=None):
        if type not in FunctionGenerator.TYPES:
            raise ValueError("Type must be one of %s" % (TYPES,))
        self.command("APPL:%s %s,%s,%s" % (type, fmt(freq), fmt(amp), fmt(offset)))

    def __set_amplitude(self, voltage):
        self.command("VOLT %s" % fmt(voltage))
    def __get_amplitude(self):
        return float(self.query("VOLT?"))
    amplitude = property(__get_amplitude, __set_amplitude)

    def __set_frequency(self, frequency):
        self.command("FREQ %s" % fmt(frequency))
    def __get_frequency(self):
        return float(self.query("FREQ?"))
    frequency = property(__get_frequency, __set_frequency)

    def __set_offset(self, offset):
        self.command("OFFS %s" % fmt(offset))
    def __get_offset(self):
        return float(self.query("OFFS?"))
    offset = property(__get_offset, __set_offset)

    def __set_load(self, load):
        if load not in FunctionGenerator.LOADS:
            raise ValueError("Load value must be in %s" % (LOADS,))
        self.command("OUTP:LOAD %s" % load)
    def __get_load(self):
        load = float(self.query("OUTP:LOAD?"))
        return LOAD_50OHMS if load == 50.0 else LOAD_INFINITY
    load = property(__get_load, __set_load)


    def upload_waveform(self, waveform):
        if len(waveform) < 8 or len(waveform) > 16000:
            raise ValueError("Waveform must be between 8 and 16000 points")
        waveform = map(str, map(fmt, normalize(waveform)))
        cmd = "DATA VOLATILE,%s" % ",".join(waveform)
        print cmd
        self.command(cmd)


    def download_waveform(self):
        pass

    def use_arbitrary_waveform(self, name='VOLATILE'):
        self.command("FUNC:USER %s" % name)

