from __future__ import with_statement
from common import Instrument
from processing import *
import time

ANALOG_1 = "CHAN1"
ANALOG_2 = "CHAN2"
ANALOG = (ANALOG_1, ANALOG_2)

DIGITAL_0 = "DIG0"
DIGITAL_1 = "DIG1"
DIGITAL_2  = "DIG2"
DIGITAL_3  = "DIG3"
DIGITAL_4 = "DIG4"
DIGITAL_5 = "DIG5"
DIGITAL_6 = "DIG6"
DIGITAL_7 = "DIG7"
DIGITAL_8 = "DIG8"
DIGITAL_9 = "DIG9"
DIGITAL_10 = "DIG10"
DIGITAL_11 = "DIG11"
DIGITAL_12 = "DIG12"
DIGITAL_13 = "DIG13"
DIGITAL_14 = "DIG14"
DIGITAL_15 = "DIG15"
DIGITAL = (DIGITAL_0, DIGITAL_1, DIGITAL_2, DIGITAL_3, DIGITAL_4, DIGITAL_5, DIGITAL_6, DIGITAL_7, DIGITAL_8, DIGITAL_9, DIGITAL_10,DIGITAL_11,DIGITAL_12,DIGITAL_13,DIGITAL_14,DIGITAL_15)

CHANNELS = tuple(ANALOG + DIGITAL)

POD1 = "POD1"
POD2 = "POD2"
PODS = (POD1, POD2)

MATH = "MATH"

AC = "AC"
DC = "DC"
GND = "GND"
COUPLINGS = (AC, DC, GND)

EXT = "EXT"
TRIGGER_SOURCES = tuple(ANALOG + DIGITAL + (EXT,))

X1 = "X1"
X2 = "X2"
Y1 = "Y1"
Y2 = "Y2"
CURSORS = (X1,X2,Y1,Y2)

RISING = "POS"
FALLING = "NEG"
SLOPES = (RISING, FALLING)

NORMAL = "NORMAL"
AUTO = "AUTO"
AUTO_LEVEL = "AUTOL"

CMOS = "CMOS"
ECL = "ECL"
TTL = "TTL"
THRESHOLDS = (CMOS, ECL, TTL)

PERIOD = "PER"
PHASE = "PHAS"
PRESHOOT = "PRES"
PULSE_WIDTH = "PWID"

class Channel(object):
    
    def __init__(self, parent, name):
        self.scope = parent
        self.name = name
        self.last_label = None

    def __get_visible(self):
        return bool(int(self.scope.query(":%s:DISP?" % self.name)))
    def __set_visible(self, v):
        if v:
            self.scope.command(":%s:DISP 1" % self.name)
        else:
            self.scope.command(":%s:DISP 0" % self.name)
    visible = property(__get_visible, __set_visible)

    def show(self):
        self.visible = True

    def hide(self):
        self.visible = False

    def __set_label(self, label):
        label = str(label)
        self.scope.command(':%s:LAB "%s"' % (self.name, ("%-6s" % label).strip()))

    def __get_label(self):
        return self.scope.query(":%s:LAB?" % self.name)[1:-1]
    label = property(__get_label, __set_label)

    def save_label(self):
        self.last_label = self.label
        return self.label

    def restore_label(self, label=None):
        if label == None:
            if self.last_label == None:
                raise Exception("Can't restore label.  No saved label provided!")
            self.label = self.last_label
        else:
            self.label = label

    def get_rawdata(self, points=1000):
        raise NotImplementedError()

    def get_data(self, points=1000):
        y = self.get_rawdata(points=points)
        xinc, xorigin, xreference = map(float, self.scope.commands([ (":WAV:XINC?",QUERY_ASCII), (":WAV:XOR?",QUERY_ASCII), (":WAV:XREF?",QUERY_ASCII)]))
        x = list(y) 
        for i in range(len(x)):
            x[i] = xorigin+xinc*(i-xreference)
        return x,y

    def save_data(self, filename, points=1000):
        x, y = self.get_data(points=points)
        with open(filename, 'w') as fp:
            for x,y in zip(x,y):
                fp.write("%g,%g\n" % (x,y))

    def __eq__(self, x):
        try: return x.name == self.name
        except:
            try:
                return x == self.name
            except:
                return False

class DigitalChannel(Channel):

    def __init__(self, parent, name):
        Channel.__init__(self, parent.scope, name)
        self.pod = parent

    def __get_threshold(self):
        return None

    def __set_threshold(self, value):
        if value not in THRESHOLDS:
            value = "+%0.2f" % value
        self.scope.command("DIG%s:THR %s" % (self.name, value))
    threshold = property(__get_threshold, __set_threshold)

    def __get_position(self):
        return int(self.scope.query("%s:POS?" % self.name))

    def __set_position(self, pos):
        self.scope.command("%s:POS %d" % (self.name, pos))
    position = property(__get_position, __set_position)

    def get_rawdata(self, points=1000):
        time, raw_data = self.pod.get_rawdata(points)
        return time, raw_data[self.name]

def channel2name(channel):
    if isinstance(channel, Channel):
        return channel.name
    elif isinstance(channel, str):
        return channel
    raise Exception("%s is not a valid channel." % channel)

class Pod(object):

    def __init__(self, parent, name):
        self.scope = parent
        self.name = name
        self.__channels = {}
        self.channels = []
        if self.name == POD1:
            for name in (DIGITAL_0, DIGITAL_1, DIGITAL_2, DIGITAL_3, DIGITAL_4, DIGITAL_5, DIGITAL_6, DIGITAL_7):
                self.channels.append(DigitalChannel(self, name))
                self.__channels[name] = self.channels[-1]
        elif self.name == POD2:
            for name in (DIGITAL_8, DIGITAL_9, DIGITAL_10, DIGITAL_11, DIGITAL_12, DIGITAL_13, DIGITAL_14, DIGITAL_15):
                self.channels.append(DigitalChannel(self, name))
                self.__channels[name] = self.channels[-1]

    def __iter__(self):
        return iter(self.channels)

    def __getitem__(self, item):
        try:
            return self.__channels[item]
        except:
            channel = self.scope.get_channel_from_label(item)
            if channel in self.channels:
                return channel
            else:
                raise KeyError("Pod does not have channel %s" % item)

                    
    def __contains__(self, item):
        try:
            self[item]
            return True
        except:
            return False

    def get_rawdata(self, points=1000):
        if points not in (100, 200, 500, 1000, 2000, None):
            raise ValueError("Number of points for acquisition should be 100, 200, 500, 1000 or 2000")
        if points == None:
            points = "MAX"

        response=self.scope.commands([  (":WAV:XINC?", QUERY_ASCII),
                                        (":WAV:XOR?", QUERY_ASCII),
                                        (":WAV:XREF?", QUERY_ASCII),
                                        (":TIM:MODE NORM",QUERY_NONE),
                                        (":ACQ:TYPE NORM",QUERY_NONE),
                                        (":WAV:SOUR %s" % self.name, QUERY_NONE),
                                        (":WAV:FORM BYTE",QUERY_NONE),
                                        (":WAV:POIN %s" % str(points), QUERY_NONE),
                                        (":WAV:DATA?", QUERY_BINARY)])
        dataStr = response[-1]
        xinc, xorigin, xreference = map(float, response[0:3])
        t = list(dataStr)
        for i in range(len(t)):
            t[i] = xorigin+xinc*(i-xreference)
        
        if dataStr:
            retval = {}
            try:
                result = map(ord,dataStr)
            except:
                self.scope.errors()
                raise

            for i,key in enumerate([channel.name for channel in self.channels]):
                retval[key] = []
                for j in result:
                    retval[key].append(1 if bool(j & (1 << i)) else 0)
            return t,retval
        else:
            raise Exception("No data returned.  Waveform buffer is empty.")
            self.errors()

    def get_data(self, points=1000):
        t,data = self.get_rawdata(points=points)
        return t, data


class AnalogChannel(Channel):

    def __init__(self, *args, **kwargs):
        Channel.__init__(self, *args, **kwargs)

    def __set_coupling(self, coupling):
        coupling = coupling.strip().upper()
        if coupling not in COUPLINGS: 
            raise TypeError("Invalid channel coupling specified")
        self.scope.command(":"+self.name+":COUP "+coupling.strip().upper())
    def __get_coupling(self):
        return self.scope.query(":"+self.name+":COUP?")
    coupling = property(__get_coupling, __set_coupling)

    @property
    def max(self):
        return float(self.scope.query(":MEAS:VMAX? %s" % self.name))
    
    @property
    def min(self):
        return float(self.scope.query(":MEAS:VMIN? %s" % self.name))
    
    @property
    def avg(self):
        return float(self.scope.query(":MEAS:VAV? %s" % self.name))

    @property
    def amplitude(self):
        return float(self.scope.query(":MEAS:VAMP? %s" % self.name))

    @property
    def duty_cycle(self):
        return float(self.scope.query(":MEAS:DUTY? %s" % self.name))
   
    @property
    def rise_time(self):
        return float(self.scope.query(":MEAS:RIS? %s" % self.name))

    @property
    def fall_time(self):
        return float(self.scope.query(":MEAS:FALL? %s" % self.name))
    
    @property
    def frequency(self):
        return float(self.scope.query(":MEAS:FREQ? %s" % self.name))

    @property
    def pwidth(self):
        return float(self.scope.query(":MEAS:PWIDTH? %s" % self.name))

    @property
    def nwidth(self):
        return float(self.scope.query(":MEAS:NWIDTH? %s" % self.name))
    
    @property
    def base(self):
        return float(self.scope.query(":MEAS:VBAS? %s" % self.name))

    @property
    def top(self):
        return float(self.scope.query(":MEAS:VTOP? %s" % self.name))
    
    @property
    def overshoot(self):
        return float(self.scope.query(":MEAS:OVER? %s" % self.name))

    @property
    def undershoot(self):
        return float(self.scope.query(":MEAS:PRES? %s" % self.name))

    @property
    def phase(self):
        return float(self.scope.query(":MEAS:PHAS? %s" % self.name))

    def get_rawdata(self, points=1000):
        if points not in (100, 200, 500, 1000, 2000, None):
            raise ValueError("Number of points for acquisition should be 100, 200, 500, 1000 or 2000")
        if points == None:
            points = "MAX"
        dataStr=self.scope.commands([   (":TIM:MODE NORM",False),
                                        (":ACQ:TYPE NORM",False),
                                        (":WAV:SOUR %s" % self.name, False),
                                        (":WAV:FORM ASCII",False),
                                        (":WAV:POIN %s" % str(points), False),
                                        (":WAV:DATA?", True)])[-1]

        if dataStr:
            return map(float,dataStr[int(dataStr[1])+2:len(dataStr)].replace(" ","").split(","))
        else: 
            raise Exception("No data returned.  Waveform buffer is empty.")

    def get_rawdata_binary(self, points=1000):
        dataStr=self.scope.commands([   (":TIM:MODE NORM",False),
                                        (":ACQ:TYPE NORM",False),
                                        (":WAV:SOUR %s" % self.name, False),
                                        (":WAV:FORM WORD",False),
                                        (":WAV:POIN %s" % str(points), False),
                                        (":WAV:PRE?", QUERY_ASCII),
                                        (":WAV:DATA?", QUERY_BINARY)])[-2:]
        return dataStr

class MathChannel(AnalogChannel):

    def __init__(self, *args, **kwargs):
        AnalogChannel.__init__(self, *args, **kwargs)

    def __get_coupling(self):
        raise AttributeError
    def __set_coupling(self, x):
        raise AttributeError
    coupling = property(__get_coupling, __set_coupling)


class Cursor(object):

    def __init__(self, parent, name):
        self.name = name
        self.scope = parent

    def __get_position(self):
        self.scope.command("MARK:%sP?" % self.name)

    def __set_position(self, pos):
        pos = float(pos)
        self.scope.command("MARK:%sP %f" % (self.name, pos))

    pos = property(__get_position, __set_position)

class StandardTrigger(object):

    def __init__(self, parent):
        self.scope = parent

    def __set_source(self, source):
        try:
            source = self.scope[source]
        except:
            raise ValueError("%s not a valid trigger source." % source)
        self.scope.command(":TRIG:SOUR %s" % source.name)
    def __get_source(self):
        return self.scope[self.scope.query(":TRIG:SOUR?")]
    source = property(__get_source, __set_source)

    def __set_coupling(self, source):
        if coupling not in COUPLINGS:
            raise ValueError("%s not a valid trigger coupling. Must be %s." % (source, COUPLINGS))
        self.scope.command(":TRIG:COUP %s" % source)
    def __get_coupling(self):
        return self.scope.command(":TRIG:COUP?")
    coupling = property(__get_coupling, __set_coupling)
    
    def __get_sweep(self):
        return self.scope.command(":TRIG:SWEEP?")
    def __set_sweep(self, value):
        if value not in (NORMAL, AUTO, AUTO_LEVEL):
            raise ValueError("%s not a valid trigger sweep." % value)
        return self.scope.command(":TRIG:SWEEP %s" % value)
    sweep = property(__get_sweep, __set_sweep)

class EdgeTrigger(StandardTrigger):

    def __init__(self, *args, **kwargs):
        StandardTrigger.__init__(self, *args, **kwargs)

    def __set_slope(self, slope):
        if slope not in SLOPES:
            raise ValueError("%s not a valid trigger slope. Must be %s" % (slope, SLOPES))
        self.scope.command(":TRIG:SLOP %s" % slope)
    def __get_slope(self):
        return self.scope.query(":TRIG:SLOP?")
    slope = property(__get_slope, __set_slope)

    def __set_level(self, level):
        pass


class Scope(Instrument):
    """
    A class for controlling the Agilent 54622D Mixed Signal Oscilloscope
    """
    BMP = 0
    PNG = 1

    def __init__(self,port="COM1",baud=57600, timeout=5, verbose=False):
        """
        Creates a connection to the serial port with the specified settings.
        
        comPortName -> COM port name. Form: 'COM1'
        baudRate -> Baud rate. Possible values: 9600, 19200, 38400, or 57600
        timeout -> Maximum time in seconds to wait for scope to respond.
                   Possible values: an int >= 0
        """
        Instrument.__init__(self, port=port, baud=baud, timeout=timeout, verbose=verbose)
        self.channels = {} 
        self.cursors = {}
        self.pods = {}

        # Channels
        self.channels[ANALOG_1] = AnalogChannel(self, ANALOG_1)
        self.channels[ANALOG_2] = AnalogChannel(self, ANALOG_2)
        self.channels[MATH] = MathChannel(self, MATH)

        
        self.pods[POD1] = Pod(self,POD1)
        self.pods[POD2] = Pod(self,POD2)

        # Cursors
        self.cursors[X1] = Cursor(self, X1)
        self.cursors[X2] = Cursor(self, X2)
        self.cursors[Y1] = Cursor(self, Y1)
        self.cursors[Y2] = Cursor(self, Y2)

        self.x1 = self.cursors[X1]
        self.x2 = self.cursors[X2]
        self.y1 = self.cursors[Y1]
        self.y2 = self.cursors[Y2]

        self.pod1 = self.pods[POD1]
        self.pod2 = self.pods[POD2]

        self.a1 = self[ANALOG_1]
        self.a2 = self[ANALOG_2]
        self.math = self[MATH]

        self.d0 = self[DIGITAL_0]
        self.d1 = self[DIGITAL_1]
        self.d2 = self[DIGITAL_2]
        self.d3 = self[DIGITAL_3]
        self.d4 = self[DIGITAL_4]
        self.d5 = self[DIGITAL_5]
        self.d6 = self[DIGITAL_6]
        self.d7 = self[DIGITAL_7]
        self.d8 = self[DIGITAL_8]
        self.d9 = self[DIGITAL_9]
        self.d10 = self[DIGITAL_10]
        self.d11 = self[DIGITAL_11]
        self.d12 = self[DIGITAL_12]
        self.d13 = self[DIGITAL_13]
        self.d14 = self[DIGITAL_14]
        self.d15 = self[DIGITAL_15]

        
        self.saved_setup = None
    
    def __str__(self):
        return "<Agilent 54622D on %s @ %d Baud>" % (self.comPortName, self.baudRate)

    def __repr__(self):
        return str(self)

    def __iter__(self):
        return iter([self.a1, self.a2, self.d0, self.d1, self.d2, self.d3, self.d4, self.d5, self.d6, self.d7, self.d8, self.d9, self.d10, self.d11, self.d12, self.d13, self.d14, self.d15])

    def clear_labels(self):
        for channel in self:
            channel.label = ""

    def set_labels(self, labels):
        for channel in labels:
            self[channel].label = labels[channel]

    def __getitem__(self, key):
        for x in (self.channels, self.cursors) + tuple(self.pods.values()) + (self.pods,):
            try:
                return x[key]
            except:
                continue
        
        if key in self:
            return key
       
        return self.get_channel_from_label(key)


    def single(self):
        """
        Aquire a single trigger of data.
        """
        self.command(":SING")

    def run(self):
        """
        Begin repetetive aquisitions.
        """
        self.command(":RUN")

    def digitize(self):
        self.command(":DIG")

    def __set_lock(self, lock):
        self.command(":SYST:LOCK %d" % (1 if bool(lock) else 0))

    def lock(self):
        self.__set_lock(True)
    def unlock(self):
        self.__set_lock(False)

    def __screenshot(self):
        self.errors()
        self.port.open()
        try:
            cmd = ":DISP:DATA? TIFF,SCR"
            #print "--> '%s'" % cmd 
            self.port.write(cmd + '\n')

            resp = self.port.read(2)
            pound, digits = resp
            #print "<-- '%s'" % resp
            if pound != "#": raise Exception("Unexpected response in screenshot acquisition.")
            try: digits =int(digits)
            except: raise Exception("Could not read screenshot block size.")
            try: size = int(self.port.read(digits))
            except: raise Exception("Could not read screenshot block size.")
            retval = ''
            # Hack so we get ALL the data from the slow-ass scope.
            while len(retval) < size:
                retval += self.port.read()
            #print "<-- <%d bytes of binary data>" % len(retval)
            
        except:
            self.port.close()
            raise
        self.port.close()
        return retval

    def take_screenshot(self, filename=None):
        if filename == None:
            filename = time.strftime("screen_%Y%m%d%H%M%S.png")
        
        screen_data = self.__screenshot()
        try:
            import ImageFile
        except:
            fp = open(filename, 'wb')
            fp.write(screen_data)
            fp.close()
            return
        p = ImageFile.Parser()
        p.feed(screen_data)
        im = p.close()
        im.save(filename)
        return screen_data

    def get_screenshot(self, format=0):
        screen_data = self.__screenshot()
        if format == Scope.BMP:
            return screen_data
        elif format == Scope.PNG:
            import ImageFile, StringIO
            p = ImageFile.Parser()
            p.feed(screen_data)
            im = p.close()
            fp = StringIO.StringIO()
            im.save(fp, "PNG")
            value = fp.getvalue()
            fp.close()
            return value
        else:
            raise ValueError("Invalid image type.")
    def acquire(self, waveforms, points=1000):
        # TODO, UPDATE THIS TO INCLUDE ANALOG STUFF
        t = []
        get_pod1=get_pod2=False
        for waveform in waveforms:
            if waveform in self[POD1]:
                get_pod1=True
            elif waveform in self[POD2]:
                get_pod2=True 
        data = {}
        if get_pod1:
            t, d = self.pod1.get_data(points=points)
            data.update(d)
        if get_pod2:
            t, d = self.pod2.get_data(points=points)
            data.update(d)

        retval = {}
        for waveform in waveforms:
            name = self[waveform].name
            if name in data:
                retval[waveform] = data[name]
            else:
                t, d = self[waveform].get_data(points=points)
                retval[waveform] = d

        return t, retval

    def get_labels(self, *channels):
        channels = channels or ANALOG + DIGITAL
        retval = {}
        for channel in channels:
            retval[channel] = self[channel].save_label()
        return retval

    def save_labels(self, *channels):
        self.last_labels = self.get_labels(*channels)
        return self.last_labels

    def clear_labels(self, *channels):
        channels = channels or ANALOG + DIGITAL
        for channel in channels:
            self[channel].label = ""

    def get_channel_from_label(self, label):
        for channel in self:
            if channel.label.upper().strip() == label.upper().strip():
                return channel
        raise ValueError("No channel with label %s" % label)

    def restore_labels(self, labels=None):
        if labels == None:
            if self.last_labels==None:
                raise Exception("Cannot restore labels.  No previous labels saved!")
            for channel in self.last_labels:
                self[channel].restore_label(self.last_labels[channel])
        else:
            for channel in labels:
                self[channel].restore_label(labels[channel])

    def __get_serial_number(self):
        return self.query(":SER?")
    serial_number = property(__get_serial_number)

    def stop(self):
        self.command(":STOP")

    def auto_scale(self):
        self.command(":AUT")

    def stack_digital_channels(self, bottom=0):
        channels =  [(channel, channel.position) for channel in list(self.pod1) + list(self.pod2) if channel.visible]
        channels.sort(lambda x,y : cmp(x[1],y[1]))
        i = bottom
        for channel, position in channels:
            channel.position = i
            i+=1

    def decode_i2c(self, sda=ANALOG_1, scl=ANALOG_2, points=1000):
        t, channels = self.acquire((sda, scl), points=points)
        i2can = I2CAnalyzer(t, sda=channels[sda], scl=channels[scl])
        return i2can.transactions()

    def decode_spi(self, miso='MISO', mosi='MOSI', sck='SCK', cs='CS', points=1000):
        t, channels = self.acquire((miso, mosi, sck, cs), points=points)
        analyzer = SPIAnalyzer(t, channels[miso], channels[mosi], channels[sck], channels[cs])
        return analyzer.transactions()

    def show(self, transaction):
        self[X1].pos = transaction.timebase[0]
        self[X2].pos = transaction.timebase[-1]

    def display_message(self, message):
        message = str(message)
        if len(message) > 255: message=message[0:255]
        self.command(':SYST:DSP "%s"' % message)
    
    def type_message(self, message, rate=10.0):
        message = str(message)
        if len(message) > 255:
            message=message[0:255]
        for i in range(1,len(message)+1):
            self.display_message(message[0:i])
            time.sleep(1.0/rate)

    def clear_message(self):
        self.display_message("")

    def reset(self):
        self.command("*RST")

    def __get_trigger(self):
        type = self.query(":TRIG:MODE?")
        if type == "EDGE":
            return EdgeTrigger(self)
        else:
            return None
    trigger = property(__get_trigger)

    def get_data(self, *channels):
        retval = []
        for channel in channels:
            x,y = self[channel].get_data()
            retval.append(y)
        retval = [x] + retval
        return retval

    def __get_setup(self):
        return self.query(":SYST:SET?", type=QUERY_BINARY)

    def __set_setup(self, setup_data):
        self.command(":SYST:SET #8%08d%s" % (len(setup_data), setup_data))

    setup = property(__get_setup, __set_setup, doc="System setup data  (binary format)")


    def save_setup(self, filename=None):
        if not filename:
            self.saved_setup = self.setup
        else:
            with open(filename, 'wb') as fp:
                fp.write(self.setup)

    def restore_setup(self, filename=None):
        if filename:
            with open(filename, 'rb') as fp:
                self.setup = fp.read()
        else:
            if self.saved_setup:
                self.setup = self.saved_setup
            else:
                raise Exception("No saved setup data, and no setup file specified.")

