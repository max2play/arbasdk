"""
    Arbalet - ARduino-BAsed LEd Table
    ArduinoLink - Arbalet Link to the hardware table using Arduino

    Handle the connection to Arduino

    Copyright 2015 Yoan Mollard - Arbalet project - http://github.com/arbalet-project
    License: GPL version 3 http://www.gnu.org/licenses/gpl.html
"""
from __future__ import print_function  # py2 stderr
from .abstract import AbstractLink
from serial import Serial, SerialException
from struct import pack, unpack, error
from sys import stderr
from os import name

__all__ = ['ArduinoLink']

class ArduinoLink(AbstractLink):
    CMD_HELLO = b'H'
    CMD_BUFFER_READY = b'B'
    CMD_BUFFER_READY_DATA_FOLLOWS = b'D'
    CMD_CLIENT_INIT_SUCCESS = b'S'
    CMD_CLIENT_INIT_FAILURE = b'F'
    PROTOCOL_VERSION = 2
    SKIPONE = 0
    DEFAULTKEYS = [0,0,0,0,0,0,0,0,0,0,0,0,0]

    def __init__(self, arbalet, diminution=1):
        super(ArduinoLink, self).__init__(arbalet, diminution)
        self._current_device = 0
        self._serial = None
        self._diminution = diminution
        self._arbalet = arbalet
        self._connected = False

        if name=='nt':  # reserved names: 'posix', 'nt', 'os2', 'ce', 'java', 'riscos'
            self._platform = 'windows'
        else:
            self._platform = 'unix'

        self.start()

    def connect(self):
        print("Arduino: Starting Connect")
        if self.is_connected():
            print("Arduino: TEST - keep intact connection...")
            return True
        if self._serial:
            print("Arduino: Closing former connection")
            self._serial.close()
        device = self._arbalet.config['devices'][self._platform][self._current_device]
        try:
            self._serial = Serial(device, self._arbalet.config['speed'], timeout=3)
        except SerialException as e:
            print("[Arbalink] Connection to {} at speed {} failed: {}".format(device, self._arbalet.config['speed'], str(e)), file=stderr)
            self._serial = None
            self._current_device = (self._current_device+1) % len(self._arbalet.config['devices'])
            return False
        else:
            try:
                self.handshake()
            except (IOError, SerialException, OSError, ValueError) as e:
                print("[Arbalink] Handshake failure: {}".format(str(e)), file=stderr)
                return False
            return True

    def is_connected(self):
        return self._serial is not None and self._serial.isOpen() and self._connected

    def read_uint8(self):
        return ord(self.read_char())

    def write_uint8(self, i):
	self._serial.write(pack('<B', i))

    def read_char(self):
        try:
            test = unpack('<c', self._serial.read());
 	    #print("Read_char")
	    #print(test)
	    return test[0]
        except error:
            self._connected = False
            return '\0'

    def write_char(self, c):
        #print("write char")
	self._serial.write(pack('<c', bytes(c)))

    def read_short(self):
        try:
            if self.SKIPONE == 1:
	        test = [1001]
		self.SKIPONE = 0
	    else:
	        test = unpack('<H', self._serial.read(2));
	    #print(test[0])
	    if test[0] > 17000 and test[0] < 60000:
		test = [1001]
		#print("Error - 1 Byte sent wrong, corrected")
		self._serial.read(1);
		self.SKIPONE = 1
	    return test[0]
        except error:
            self._connected = False
            return 0

    def write_short(self, s):
	#print("write short")
        self._serial.write(pack('<H', s))

    def handshake(self):
        self._connected = False
        hello = self.read_char()
        if hello == self.CMD_HELLO:
            self.write_char(self.CMD_HELLO)
            version = self.read_uint8()
            assert version != self.CMD_HELLO, "Hardware has reset unexpectedly during handshake, check wiring and configuration file"
            assert version == self.PROTOCOL_VERSION, "Hardware uses protocol v{}, SDK uses protocol v{}".format(version, self.PROTOCOL_VERSION)
            self.write_short(self._arbalet.end_model.get_height()*self._arbalet.end_model.get_width())
            self.write_uint8(self._arbalet.config['leds_pin_number'])
            self.write_uint8(self._arbalet.config['touch']['num_keys'])
            init_result = self.read_char()
            if init_result == self.CMD_CLIENT_INIT_SUCCESS:
                print("Arbalet hardware initialization successful")
                self._connected = True
                return True
            elif init_result == self.CMD_CLIENT_INIT_FAILURE:
                raise ValueError("Arduino can't allocate memory, init failure")
            else:
                raise ValueError("Expected one command of {}, got {}".format([self.CMD_CLIENT_INIT_SUCCESS, self.CMD_CLIENT_INIT_FAILURE], init_result))
        else:
            raise ValueError("Expected command {}, got {} ({})".format(self.CMD_HELLO, hello, ord(hello)))

    def get_serial_frame(self, end_model):
        frame = end_model.data_frame
        
        array = bytearray(' '*(end_model.get_height()*end_model.get_width()*3), 'ascii')
        for h in range(end_model.get_height()):
            for w in range(end_model.get_width()):
                idx = self.map_pixel_to_led(h, w)*3 # = mapping shift by 3 colors
                array[idx] = frame[h][w][0]
                array[idx+1] = frame[h][w][1]
                array[idx+2] = frame[h][w][2]
        return array

    def read_touch_frame(self):
        try:
            touch_int = self.read_short()
            #print(touch_int)
            num_keys = self._arbalet.config['touch']['num_keys']
            keys = []
	    counter = 0
            for key in range(num_keys):
                # FIX HERE BYTETRANSFER Problem
		key_state = self.read_short()
                if key_state > 1000 and key_state < 60000:
		    keys.append(self.DEFAULTKEYS[counter])
		else:
		    keys.append(key_state)
		    self.DEFAULTKEYS[counter] = key_state
		counter +=1
	    #print(keys)
        except (IOError, SerialException,) as e:
            self._serial.close()
            self._connected = False
        else:
            if self._arbalet.touch is not None and self._arbalet.config['touch']['num_keys'] > 0:
                self._arbalet.touch.create_event(touch_int, keys)

    def write_led_frame(self, end_model):
        try:
            ready = self.read_char()
            commands = [self.CMD_BUFFER_READY, self.CMD_BUFFER_READY_DATA_FOLLOWS]
            if ready in commands:
                frame = self.get_serial_frame(end_model)
                #print(frame)
		self._serial.write(frame)
            elif len(ready)>0:
                #raise ValueError("Expected one command of {}, got {}".format(commands, ready))
		ready = '';
		print("skip value error")
        except (IOError, SerialException, ) as e:
            self._serial.close()
            self._connected = False
        else:
            data_follows = ready == self.CMD_BUFFER_READY_DATA_FOLLOWS
            return data_follows

    def close(self):
        super(ArduinoLink, self).close()
        if self._serial:
            self._serial.close()
            self._serial = None
