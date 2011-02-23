from __future__ import with_statement 
import time
import serial


QUERY_NONE = 0
QUERY_ASCII = 1
QUERY_BINARY = 2

class Instrument(object):
    '''
    Abstract baseclass for Agilent HPIB Instruments that can chat over RS-232
    '''
    def __init__(self,port="COM1",baud=57600, timeout=5, verbose=False, rtscts=False, dsrdtr=False, stopbits=serial.STOPBITS_ONE):
        """
        Creates a connection to the serial port with the specified settings.
        
        comPortName -> COM port name. Form: 'COM1'
        baudRate -> Baud rate. Possible values: 9600, 19200, 38400, or 57600
        timeout -> Maximum time in seconds to wait for scope to respond.
                   Possible values: an int >= 0
        """
        self.comPortName=port
        self.baudRate=baud
        self.timeout=timeout

        self.port=serial.Serial(port=self.comPortName,baudrate=self.baudRate,timeout=self.timeout, rtscts=rtscts, dsrdtr=dsrdtr, stopbits=stopbits)
        self.port.flush()
        self.port.flushInput()
        self.port.close()
        self.verbose = verbose

    def query(self,query,type=QUERY_ASCII):
        return self.commands(((query, type),))[0]

    def command(self,command):
        self.commands(((command,False),))

    def commands(self, commands):
        self.errors()
        self.port.open()
        result = None
        # Make sure we clear the scope output before executing commands
        commands = [("*CLS", QUERY_NONE)] + list(commands) 
        result = []
        try:
            for command, query in commands:
                if self.verbose:
                    print "--> '%s'" % command
                self.port.write(command+"\n")
                if query == QUERY_ASCII:
                    s = self.port.readline().strip()
                    if self.verbose:
                        print "<-- '%s'" % s
                    result.append(s)
                elif query == QUERY_BINARY:
                    pound, digits = self.port.read(2)
                    if pound != "#": raise Exception("Unexpected response in binary query.")
                    try: digits =int(digits)
                    except: raise Exception("Could not read binary query header.")
                    try: size = int(self.port.read(digits))
                    except: raise Exception("Could not read binary query block size.")
                    binstring = ''
                    while len(binstring) < size:
                        binstring += self.port.read()
                    result.append(binstring)
                    if self.verbose:
                        if len(binstring) > 0:
                            print "<-- <%d bytes of binary data>" % len(binstring)
                else:
                    result.append(None)
        except:
            self.port.close()
            raise
        self.port.close()
        self.errors(True)
        return result[1:]

    def errors(self, raise_errors=False):
        """
        Returns all errors from the scope's error queue.
        """
        self.port.open()
        try:
            errors=[]
            self.port.write(":SYSTEM:ERR?\n")
            error=self.port.readline()
            while error.find("+0") is -1 and error is not '':
                errors.append(error)
                self.port.write(":SYSTEM:ERR?\n")
                error=self.port.readline()
            self.port.flush()
            self.port.flushInput()
        except:
            self.port.close()
            raise
        self.port.close()
        if raise_errors:
            if errors:
                raise Exception(errors[0])
        return errors


def format_number(x):
    if x == None:
        return "DEF"
    return ("%g" % x).upper()

if __name__ == '__main__':
    scope=Scope(port="COM1", baudRate=57600)

