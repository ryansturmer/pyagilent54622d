import agilent

class LogicAnalyzer(object):

    def __init__(self, timebase):
        self.timebase = timebase
        self.waveforms = {}
        self.digitized_waveforms = {}

    def slice(self, start, end):
        a = self.index(start)
        b = self.index(end)
        retval = LogicAnalyzer(self.timebase[a:b])
        for key in self.waveforms:
            retval.waveforms[key] = self.waveforms[key][a:b]
            retval.digitized_waveforms[key] = self.digitized_waveforms[key][a:b]
        return retval

    def __setitem__(self, key, value):
        if len(value) != len(self.timebase):
            raise ValueError("Waveform data does not match the timebase for this analyzer.")

        # Store the original waveform
        self.waveforms[key] = value

        # Digitize the waveform, store that as well
        avg = (max(value)-min(value))/2.0
        waveform = [1 if x > avg else 0 for x in value]
        self.digitized_waveforms[key] = waveform

    def __getitem__(self, key):
        return self.waveforms[key]

    def first_edge_after(self, key, time):
        for edge in self.edges(key):
            if edge > time: return edge
        return None

    def rising_edges(self, key):
        retval = []
        waveform = self.digitized_waveforms[key]
        for i in range(len(waveform)-1):
            if waveform[i] < waveform[i+1]:
                retval.append(self.timebase[i])
        return retval

    def falling_edges(self, key):
        retval = []
        waveform = self.digitized_waveforms[key]
        for i in range(len(waveform)-1):
            if waveform[i] > waveform[i+1]:
                retval.append(self.timebase[i])
        return retval

    def edges(self, key):
        '''
        Return the time from the timebase at which the provided waveform transitions from high to low or low to high.
        '''
        retval = []
        waveform = self.digitized_waveforms[key]
        for i in range(len(waveform)-1):
            if waveform[i] > waveform[i+1] or waveform[i] < waveform[i+1]:
                retval.append(self.timebase[i])
        return retval
    
    def high_ranges(self, key):
        retval = []
        waveform = self.digitized_waveforms[key]
        for i in range(1,len(waveform)-1):
            if waveform[i]:
                if not waveform[i-1]:
                    range_start = i
            else:
                if waveform[i-1]:
                    range_end = i
                    retval.append((self.timebase[range_start], self.timebase[range_end]))

        return retval

    def low_ranges(self, key):
        retval = []
        waveform = self.digitized_waveforms[key]
        range_start = 1
        for i in range(1,len(waveform)-1):
            if not waveform[i]:
                if waveform[i-1]:
                    range_start = i
            else:
                if not waveform[i-1]:
                    range_end = i
                    retval.append((self.timebase[range_start], self.timebase[range_end]))

        return retval

    def state(self, key, time):
        return bool(self.digitized_waveforms[key][self.index(time)])

    def index(self, time):
        mintime = abs(self.timebase[-1] - self.timebase[0])
        mindex = 0
        if time in self.timebase:
            return self.timebase.index(time)
        else:
            for i, t in enumerate(self.timebase):
                diff = abs(time-t)
                if diff < mintime:
                    mintime = diff
                    mindex = i
        return mindex

    def sub_range(self, range):
        a = self.index(range[0])
        b = self.index(range[1])
        retval = LogicAnalyzer(self.timebase[a:b])
        for key in self.waveforms:
            retval.waveforms[key] = self.waveforms[key][a:b]
            retval.digitized_waveforms[key] = self.digitized_waveforms[key][a:b]
        return retval

    def _bitlist_to_byte(self, bitlist):
        retval = 0
        for bit in bitlist:
            retval |= bit
            retval <<= 1
        return retval >> 1

class I2CTransaction(object):
    def __init__(self, data, acks, analyzer):
        self.raw_data = data
        self.address = data[0] >> 1
        self.readwrite = data[0] & 1
        self.payload = data[1:]
        self.acks = acks
        self.analyzer = analyzer
        self.timebase = analyzer.timebase
    
    def __str__(self):
        if self.acks:
            s = ""
            for data, ack in zip(self.payload, self.acks):
                s += "%02x! " % data if ack else "%02x " % data
            return "<I2C %s addr=0x%02x data=%s>" % ("READ" if self.readwrite else "WRITE", self.address, s.strip())
        else:
        
            return "<I2C %s addr=0x%02x %s>" % ("READ" if self.readwrite else "WRITE", self.address, " ".join(["%02x" % d for d in self.payload]).strip())
    def __repr__(self):
        return str(self)


class I2CAnalyzer(LogicAnalyzer):

    def __init__(self, timebase, sda, scl):
        LogicAnalyzer.__init__(self, timebase)
        self['SDA'] = sda
        self['SCL'] = scl

    def __clock_rate(self):
        clock_low_pulses = self.low_ranges('SCL')
        if len(clock_low_pulses) == 0:
            raise Exception("No SCL clock detected.")
        lowpulse_time = 0
        for a,b in clock_low_pulses:
            lowpulse_time += b-a
        lowpulse_time /= len(clock_low_pulses)
        return 1.0/lowpulse_time
    clock_rate = property(__clock_rate)

    def start_conditions(self):
        retval = []
        clock_time = 1.0/self.clock_rate
        data_falling = self.falling_edges('SDA')
        for t in data_falling:
            if self.state('SCL', t) and self.state('SCL', t+clock_time/2.0): retval.append(t)
        return retval

    def stop_conditions(self):
        retval = []
        clock_time = 1.0/self.clock_rate
        data_rising = self.rising_edges('SDA')
        for t in data_rising:
            if self.state('SCL', t) and self.state('SCL', t+clock_time/2.0): retval.append(t)
        return retval

    def transaction_ranges(self):
        retval = []
        starts = self.start_conditions()
        stops = self.stop_conditions()
        if len(starts) != len(stops):
            raise Exception("Mismatching start and stop conditions.")
        for i in range(len(starts)):
            start = starts[i]
            stop = stops[i]
            if stop > start:
                retval.append((start, stop))
        return retval

    def transactions(self):
        retval = []
        for range in self.transaction_ranges():
            analyzer = self.sub_range(range)
            bitlist = []
            for edge in analyzer.rising_edges('SCL')[:-1]:
                bitlist.append(1 if analyzer.state('SDA', edge) else 0)
            if len(bitlist) % 9 != 0:
                continue
            else:
                data= []
                acks= []
                i=0
                while(i<len(bitlist)):
                    byte =  self._bitlist_to_byte(bitlist[i:i+8])
                    ack = bitlist[i+8]
                    data.append(byte)
                    acks.append(ack)
                    i+=9
                retval.append(I2CTransaction(data, acks, analyzer))
        return retval

class SPITransaction(object):
    def __init__(self, outbound, inbound, mode, analyzer):
        if len(outbound) != len(inbound): raise Exception("Inbound and outbound data sizes do not match!")
        self.outbound = outbound
        self.inbound = inbound 
        self.mode = mode
        self.analyzer = analyzer
        self.timebase = analyzer.timebase
        self.cs_lead_time = analyzer.edges('SCK')[0] - analyzer.timebase[0]
        self.cs_lag_time = analyzer.timebase[-1] - analyzer.edges('SCK')[-1]
        self.data_rate = len(inbound)/(analyzer.timebase[-1] - analyzer.timebase[0])
    def pretty(self):
        
        s =  "      SPI Transaction\n"
        s += "-----------------------------\n"
        s += "        Mode: 0x%x\n" % self.mode
        s += "CS Lead Time: %gs\n" % self.cs_lead_time
        s += " CS Lag Time: %gs\n" % self.cs_lag_time
        s += "   Data Rate: %d bps\n" % self.data_rate
        s += "        Data: Outbound  Inbound\n"
        for i, (inbound, outbound) in enumerate(zip(self.inbound, self.outbound)):
            s += "         %03d: 0x%02x      0x%02x\n" % (i, outbound, inbound)
        return s
    def __len__(self):
        return len(self.outbound)

    def __str__(self):
        return "<SPI mode=0x%x (CPOL=%d CPHA=%d), %d bytes: %s (out/in)>" % (self.mode, self.pol, self.pha, len(self), (" ".join(["0x%02x/0x%02x" % (x,y) for x,y in zip(self.outbound, self.inbound)])).strip())

    def __repr__(self):
        return str(self)

    def _get_pol(self):
        return 1 if self.mode & 2 else 0
    pol = property(_get_pol)

    def _get_pha(self):
        return 1 if self.mode & 1 else 0
    pha = property(_get_pha)

    def __getitem__(self, i):
        return (self.outbound[i], self.inbound[i])

    def __iter__(self):
        return iter(zip(self.outbound, self.inbound))

class SPIAnalyzer(LogicAnalyzer):
    def __init__(self, t, miso, mosi, sck, cs, mode=None):
        LogicAnalyzer.__init__(self, t)
        self['MISO'] = miso
        self['MOSI'] = mosi
        self['SCK'] = sck
        self['CS'] = cs
        self.mode = None

    def transaction_ranges(self):
        return self.low_ranges('CS')

    def transaction_analyzers(self):
        retval = []
        for range in self.transaction_ranges():
            retval.append(self.sub_range(range))
        return retval

    def transactions(self):
        retval = []

        def nearest_difference(p,l):
            return min([abs(p-x) for x in l])
        
        for analyzer in self.transaction_analyzers():
            rising_clock = analyzer.rising_edges('SCK')
            falling_clock = analyzer.falling_edges('SCK')
            if len(rising_clock) == 0 or len(falling_clock) == 0:
                raise Exception("No clock edges detected.")

            miso_edges = analyzer.edges('MISO')
            mosi_edges = analyzer.edges('MOSI')
            try:
                miso_rising = sum([nearest_difference(x, rising_clock) for x in miso_edges])/len(miso_edges)
                miso_falling = sum([nearest_difference(x, falling_clock) for x in miso_edges])/len(miso_edges)
                miso_mode = 2 if miso_rising < miso_falling else 0
            except:
                miso_mode = 0
            
            try:
                mosi_rising = sum([nearest_difference(x, rising_clock) for x in mosi_edges])/len(mosi_edges)
                mosi_falling = sum([nearest_difference(x, falling_clock) for x in mosi_edges])/len(mosi_edges)
                mosi_mode = 2 if mosi_rising < mosi_falling else 0
            except:
                mosi_mode = 0
            
            if miso_mode == None and mosi_mode != None: miso_mode = mosi_mode
            if mosi_mode == None and miso_mode != None: mosi_mode = miso_mode

            if miso_mode != mosi_mode:
                raise ValueError("Outbound and Inbound SPI modes do not match!  Master and slave are operating in different modes!")
            pha = miso_mode 
            start = analyzer.state("SCK", analyzer.timebase[0]) 
            end = analyzer.state("SCK", analyzer.timebase[-1]) 
            if start:
                pol = 1
                pha = 2 if pha == 0 else 1
            elif not start and not end:
                pol = 0
            else:
                raise ValueError("Clock phase could not be detected from the input waveform!")
            
            inbound=[]
            outbound = []
            if bool(pol) != bool(pha):
                inbound_bits = [1 if analyzer.state('MISO', x) else 0 for x in analyzer.falling_edges("SCK")]
                outbound_bits  = [1 if analyzer.state('MOSI', x) else 0 for x in analyzer.falling_edges("SCK")]
            else:
                inbound_bits = [1 if analyzer.state('MISO', x) else 0 for x in analyzer.rising_edges("SCK")]
                outbound_bits  = [1 if analyzer.state('MOSI', x) else 0 for x in analyzer.rising_edges("SCK")]
            if len(inbound_bits) % 8 != 0:
                raise ValueError("Transaction size not a multiple of 8 bits (%d)... weird!" % len(inbound_bits))
            i=0
            while(i < len(inbound_bits)):
                inbound.append(self._bitlist_to_byte(inbound_bits[i:i+8]))
                outbound.append(self._bitlist_to_byte(outbound_bits[i:i+8]))
                i+=8
            retval.append(SPITransaction(outbound, inbound, pol | pha, analyzer))
        return retval

