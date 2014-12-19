#!/usr/bin/env python

import logging
import socket
import struct

logging.getLogger('iBootInterface').addHandler(logging.NullHandler())

HELLO_STR = 'hello-000'

"""struct format:
little-endian
unsigned char command
21 char array username
21 char array password
unsigned char description
unsigned char parameters (should be padding byte or 'B' as unused)
unsigned short sequence number (uint16) - was H-2byte, set to I-4byte
"""
HEADER_STRUCT = struct.Struct('<B21s21sBBH')

COMMAND_MAP = {
    'NULL': 0,
    'SET': 1,
    'GET': 2,
    'IO': 3,
    'KEEPALIVE': 4,
    'RSS': 5,
    'RCU': 6
}

SOCKET_TIMEOUT = 10


class DXPCommand(object):
    COMMAND = None
    DESCRIPTOR_MAP = None
    DESCRIPTOR = None
    PAYLOAD_STRUCT = None
    

    def __init__(self, interface):
        self.interface = interface
        self.logger = logging.getLogger('iBootInterface')

    def _build_header(self):
        if not self.COMMAND:
            raise Exception("'COMMAND' type not specified for class")

        if not self.DESCRIPTOR_MAP:
            raise Exception("'DESCRIPTOR_MAP' not specified for class")

        if not self.DESCRIPTOR:
            raise Exception("'DESCRIPTOR' type not specified for class")
        self.logger.debug('dxpcommand.buildheader: COMMANDMAP: ' + str(COMMAND_MAP[self.COMMAND]))
        self.logger.debug('dxpcommand.buildheader: DESCRIPTORMAP: ' + str(self.DESCRIPTOR_MAP[self.DESCRIPTOR]))
        return HEADER_STRUCT.pack(COMMAND_MAP[self.COMMAND],
                                  self.interface.username,
                                  self.interface.password,
                                  self.DESCRIPTOR_MAP[self.DESCRIPTOR],
                                  0,
                                  self.interface.get_seq_num())

    def _build_payload(self, *pack_args):
        if not self.PAYLOAD_STRUCT:
            raise Exception("'PAYLOAD_STRUCT' not specified for class")

        return self.PAYLOAD_STRUCT.pack(*pack_args)

    def _get_response(self, socket):
        """
        Parse the response from the request
        """
        raise Exception('get_response method not implemented')

    def _get_boolean_response(self):
        response = self.interface.socket.recv(1)
        if not response:
            return False

        self.interface.increment_seq_num()
        self.logger.debug('dxpcommand.getboolresponse: responce: ' + str(response))
        return self._parse_bool(response)

    def _parse_bool(self, string):
        return not struct.unpack('?', string)[0]

    def do_request(self):
        header = self._build_header()
        self.logger.debug('dxpcommand.dorequest: header: ' + str(header))
        payload = self._build_payload()
        self.logger.debug('dxpcommand.dorequest: payload: ' + str(payload))
        request = header + payload
        self.logger.debug('dxpcommand.dorequest: fullrequest: ' + str(request))
        self.interface.socket.sendall(request)
        return self._get_response()

    def _do_payloadless_request(self):
        request = self._build_header()
        self.logger.debug('dxpcommand.dopayloadlessrequest: request: ' + str(request))
        self.interface.socket.sendall(request)
        return self._get_response()


class IOCommand(DXPCommand):
    COMMAND = 'IO'
    DESCRIPTOR_MAP = {
        'NULL': 0,
        'CHANGE_RELAY': 1,
        'CHANGE_RELAYS': 2,
        'GET_RELAY': 3,
        'GET_RELAYS': 4,
        'GET_INPUT': 5,
        'GET_INPUTS': 6,
        'PULSE_RELAY': 7
    }


class RelayCommand(IOCommand):
    STATE_MAP = {
        True: 1,
        False: 2,
        'NO_CHANGE': 0
    }

    def _get_response(self):
        return self._get_boolean_response()


class ChangeRelayCommand(RelayCommand):
    DESCRIPTOR = 'CHANGE_RELAY'
    PAYLOAD_STRUCT = struct.Struct('<BB')

    def __init__(self, interface, relay, state):
        super(ChangeRelayCommand, self).__init__(interface)
        self.relay = relay
        self.state = state
        self.logger = logging.getLogger('iBootInterface')

    def _build_payload(self):
        return super(ChangeRelayCommand, self)._build_payload(
            self.relay, self.STATE_MAP[self.state])
    #def _build_payload(self):
        #return super(ChangeRelayCommand, self)._build_payload(
            #self.relay, 1)

class ChangeRelaysCommand(RelayCommand):
    DESCRIPTOR = 'CHANGE_RELAYS'
    PAYLOAD_STRUCT = struct.Struct('<' + ('B' * 32))  # 32 unsigned chars

    def __init__(self, interface, relay_state_dict):
        super(ChangeRelaysCommand, self).__init__(interface)
        self.relay_state_dict = relay_state_dict
        self.logger = logging.getLogger('iBootInterface')

    def _build_payload(self):
        state_list = []

        self.logger.debug('changerelaycommand.buildpayload: relaystatedict: ' + str(self.relay_state_dict))
        
        """this may be a bug, indexing doesn't seem to line up correctly everywhere.
        System replies with zero indexing, should be conformant throughout."""
        for relay in range(32):
            if (relay) not in self.relay_state_dict:
                state_list.append(self.STATE_MAP['NO_CHANGE'])
            else:
                state_list.append(
                    self.STATE_MAP[self.relay_state_dict[relay]])

        self.logger.debug('changerelayscommand.buildpayload: state_list: ' + str(state_list))
        
        return super(ChangeRelaysCommand, self)._build_payload(*state_list)


class GetRelaysRequest(IOCommand):
    DESCRIPTOR = 'GET_RELAYS'

    def do_request(self):
        return self._do_payloadless_request()

    def _get_response(self):
        self.logger = logging.getLogger('iBootInterface')
        response = self.interface.socket.recv(self.interface.num_relays)
        self.logger.debug('getrelayrequest.getresponse: response: ' + str(response))
        if not response:
            return None
        response = struct.unpack("<c",response)
        self.logger.debug('getrelayrequest.getresponse: response-unpacked: ' + str(response))
        self.interface.increment_seq_num()
        """
        replace with built up responce dictionary instead of unreliable oneliner
        return [True if int.from_bytes(relay_status, byteorder='little') == 1 
                else False
                for relay_status in response]
        """
        """pre declare dictionary"""
        relay_dict = {} 
        for i in range(len(response)):
          relay_dict[i] = (True if int.from_bytes(response[i], byteorder='little')==1 else False)
        self.logger.debug('getrelayrequest.getresponse: relay_dict: ' + str(relay_dict))
        return relay_dict


class PulseRelayRequest(RelayCommand):
    DESCRIPTOR = 'PULSE_RELAY'
    PAYLOAD_STRUCT = struct.Struct('<BBH')

    def __init__(self, interface, relay, state, width):
        super(PulseRelayRequest, self).__init__(interface)
        self.logger = logging.getLogger('iBootInterface')
        self.relay = relay
        self.logger.debug('pulserelayrequest.init.relay: ' + str(self.relay))
        self.state = state
        self.logger.debug('pulserelayrequest.init.state: ' + str(self.state))
        self.width = width
        self.logger.debug('pulserelayrequest.init.width: ' + str(self.width))

    def _build_payload(self):
        return super(PulseRelayRequest, self)._build_payload(
            self.relay, self.STATE_MAP[self.state], self.width)


class iBootInterface(object):
    def __init__(self, ip, username, password, port=9100, num_relays=3):
        self.ip = ip
        self.username = username
        self.password = password
        self.port = port
        self.num_relays = num_relays
        self.seq_num = None
        self.socket = None
        self.logger = logging.getLogger('iBootInterface')
        self.logger.setLevel(logging.DEBUG)

    def get_seq_num(self):
        seq_num = self.seq_num
        #self.seq_num += 1 #this seems like the wrong way to do this. sequence numbers should only increment when generating a packet
        self.logger.debug('ibootintr.getseqnum: seq_num: ' + str(seq_num))
        return seq_num

    def increment_seq_num(self):
        self.seq_num += 1
        self.logger.debug('ibootintr.incrementseqnum: ' + str(self.seq_num))

    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(SOCKET_TIMEOUT)

        try:
            self.socket.connect((self.ip, self.port))
        except socket.error:
            self.logger.error('ibootintr.connect: Socket failed to connect')
            return False

        try:
            self.socket.sendall(str.encode(HELLO_STR))
            return self._get_initial_seq_num()
        except socket.error:
            self.logger.error('ibootintr.connect: Socket error')
            return False

    def _get_initial_seq_num(self):
        response = self.socket.recv(2)
        """
        this is supposed to be a 4 byte uint16 based on spec
        G2 doesn't seem to follow this to the letter. sending 2 bytes
        instead of 4. Added handling to manage both it acting right
        and wrong.
        """
        if not response:
            return False
        self.logger.debug('ibootintr.sequencenum_responce:' + str(response) + ' length: ' + str(len(response)))
        """ should seq_num be auto incremented? seems like it should be
        done when new packets are issued, not when old ones are captured"""
        self.seq_num = struct.unpack('<H', response)[0] + 1
        #if len(response) == 2:
          #self.seq_num = struct.unpack('<H', response)[0] + 1
        #elif len(respose) == 4: #uint16 is 2 bytes not 4.
          #self.seq_num = struct.unpack('<I', response)[0] + 1
        self.logger.debug('ibootintr.getinitialseq - initial sequence:' + str(self.seq_num))
        return True

    def disconnect(self):
        try:
            self.socket.close()
        except:
            pass

    def switch(self, relay, on):
        """Switch the given relay on or off"""
        self.connect()
        request = ChangeRelayCommand(self, relay, on)

        try:
            return request.do_request()
        except socket.error:
            return False
        finally:
            self.disconnect()

    def switch_multiple(self, relay_state_dict):
        """
        Change the state of multiple relays at once

        State dictionary should be of the form:
            {1: True}
        where the key is the relay and the value is the new state
        """
        self.connect()

        for relay, new_state in relay_state_dict.items():
            request = ChangeRelayCommand(self, relay, new_state)
            #self.logger.debug('ibootint.switch_multiple: request: ' + str(request))

            try:
                result = request.do_request()
                self.logger.debug('ibootint.switch_multiple: result: ' + str(result))
                if not result:
                    return False
            except socket.error:
                self.logger.error('ibootint.switch_multiple: Socket Error')
                self.disconnect()
                return False

        self.disconnect()
        return True

    def get_relays(self):
        self.connect()
        request = GetRelaysRequest(self)
        #self.logger.debug('ibootint.getrelays: request: ' + str(request))

        try:
            return request.do_request()
        except socket.error:
            return False
        finally:
            self.disconnect()

    def pulse_relay(self, relay, on, length):
        self.connect()
        request = PulseRelayRequest(self, relay, on, length)

        try:
            return request.do_request()
        except socket.error:
            return False
        finally:
            self.disconnect()
            
""" Additions by Garrett McGrath"""
def buildparser():
  parser=argparse.ArgumentParser(description="ibootpy - iBoot DxP Tool")
  parser.add_argument("ip", metavar='IP', help="IP you wish to interact with")
  parser.add_argument("user", metavar='USER', help="User Name (default: admin)",
		      default="admin", action="store")
  parser.add_argument("password", metavar='PASSWORD',
		      default="admin", action="store", help="Device Password")
  parser.add_argument('action', metavar="ACTION", 
		      choices=("on","off","toggle","status"), 
		      default="status", help = 'Action to perform on list of iBoot Devices (default status)')
  parser.add_argument("--port", help="Port to communicate with device",default=9100,type=int)
  parser.add_argument("--relays", help="Number of relays to interact with",
		      default=1,type=int)

  #parser.add_argument("-v","--verbose", help ="verbose output", action="store_true")
  return parser
  
            
def run(args=None):
  """Main entry if running as commandline program"""

  parser = buildparser()
  args = parser.parse_args()

  """configure logging to print to stderr"""
  #grab iboot logger
  logger = logging.getLogger('iBootInterface')
  #create format info
  FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  formatter = logging.Formatter(FORMAT)
  #configure stdout based handler
  shandler = logging.StreamHandler(sys.stdout)
  shandler.setFormatter(formatter)
  logger.addHandler(shandler)
  #configure logging to debug level
  logger.setLevel(logging.DEBUG)
  
  """
  steps required to interact with iboot:
  make iboot interface object
  retrieve dictionary of relays with object.get_relays 
  perform action requested by arguements either printing (status)
  or invoking actions (on/off/toggle) with object.switch_multiple
     def __init__(self, ip, username, password, port=9100, num_relays=3)
  """

  dev = iBootInterface(args.ip,
		       str.encode(args.user),
		       str.encode(args.password),
		     args.port, args.relays)
  
  """effectively a case statement for requested actions
  extremely rudimentary at this point, no sanity checking included."""
  
  if args.action == "status":
    relays=dev.get_relays()
    logger.info('status: ' + str(relays))
  elif args.action == "on":
    relays=dev.get_relays()
    logger.info('on_start: ' + str(relays))
    for relay in relays:
      relays[relay] = True
    logger.info('on_sending: ' + str(relays))
    dev.switch_multiple(relays)
    dev.switch(0,True)
    relays=dev.get_relays()
    logger.info('on_end: ' + str(relays))
  elif args.action == "off":
    relays=dev.get_relays()
    logger.info('off_start: ' + str(relays))
    for relay in relays:
      relays[relay] = False
    logger.info('off_sending: ' + str(relays))
    dev.switch_multiple(relays)
    dev.switch(0,False)
    relays=dev.get_relays()
    logger.info('off_end: ' + str(relays))
  elif args.action == "toggle":
    relays=dev.get_relays()
    logger.info('toggle_start: ' + str(relays))    
    for relay in relays:
      relays[relay] = not relays[relay]
    logger.info('toggle_sending: ' + str(relays))  
    dev.switch_multiple(relays)
    relays=dev.get_relays()
    logger.info('toggle_end: ' + str(relays))
  else:
    logger.info("invalid state request")
  
  
  return 0
  
  

if __name__ == '__main__':
  import sys
  import argparse
  sys.exit(run())