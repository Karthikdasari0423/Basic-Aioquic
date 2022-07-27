
import sys
import logging
import ssl
import asyncio
import time
from typing import Optional, cast
import threading
import random, itertools, struct
from aioquic.asyncio import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.asyncio.client import connect
from aioquic.quic.events import QuicEvent, StreamDataReceived
from aioquic.quic.logger import QuicFileLogger
logger = logging.getLogger("client")

id = 0
dd = 0
server_reply = list()


# Define how the client should work. Inherits from QuicConnectionProtocol.
# Override QuicEvent


class MyClient(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ack_waiter: Optional[asyncio.Future[None]] = None
        self.offset = 0

    def insert_timestamp(self, data, index):
        # inserting the offset,send time,index
        self.t1 = time.time()
        header = str(self.t1) + "," + str(self.offset) + "," + str(index) + ","
        header = header.encode()
        #print("current time is",self.t1)
        data = header + data
        return data

    # Assemble a query to send to the server
    async def query(self, data, index) -> None:

        query = data
        if isinstance(query, str):
            query = query.encode()
        stream_id = self._quic.get_next_available_stream_id()
        logger.debug(f"Next Stream ID will be : {stream_id}") 
        query = self.insert_timestamp(query, index)
        self._quic.send_stream_data(stream_id, bytes(query), True)
        waiter = self._loop.create_future()
        self._ack_waiter = waiter
        self.transmit()
        return await asyncio.shield(waiter)

    # Define behavior when receiving a response from the server
    def quic_event_received(self, event: QuicEvent) -> None:
        if self._ack_waiter is not None:
            if isinstance(event, StreamDataReceived):
                global dd, server_reply
                t4 = time.time()
                dd += 1
                waiter = self._ack_waiter
                if event.end_stream:
                    dd = 0
                    data = event.data
                    # print(data.decode())
                    self._ack_waiter = None
                    waiter.set_result(None)
                elif (dd == 1):
                    answer = event.data.decode()
                    t2, t3 = answer.split(",", 2)
                    mpd = ((float(t2) - float(self.t1)) + (t4 - float(t3))) / 2
                    self.offset = (float(t2) - float(self.t1)) - mpd
                else:
                    reply = event.data.decode()
                    server_reply.append(reply)
                    # print("REPLY",reply)
                # python QUIC_Client.py -k -qsize 50000 -v


class quicconnect(MyClient):
    def __init__(self, host_addr, port_nr, configuration):
        super().__init__(self)
        self.host_addr = host_addr
        self.port_nr = port_nr
        self.configuration = configuration
        self.frame_hist = list()
        self.closed = False
        self.start_thread()

    def send_thread(self):
        asyncio.run(self.run())

    def start_thread(self):
        self.x = threading.Thread(target=self.send_thread)
        self.x.start()

    def send_frame(self, frame):
        self.frame_hist.append(frame)

    def client_close(self):
        self.closed = True

    async def run(self):
        async with connect(
                self.host_addr,
                self.port_nr,
                configuration=self.configuration,
                create_protocol=MyClient,
        ) as client:
            self.client = cast(MyClient, client)
            while True:
                global id
                if (len(self.frame_hist) > 0):
                    curr_time = time.time()
                    id += 1
                    data = self.frame_hist.pop(0)
                    await self.client.query(data, id)
                else:
                    if (time.time() - curr_time > 15):
                        print("Timeout occured")
                        break
                    elif (self.closed):
                        print("Client Closed")
                        break

        # self.client.close()


class quicconnectclient():
    def __init__(self, host_addr, port_nr, verbose,md,msd,qlog):
        logging.basicConfig(
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
            level=logging.DEBUG if verbose else logging.INFO, )
        if qlog:
            self.configuration = QuicConfiguration(is_client=True, quic_logger=QuicFileLogger(qlog))
        else:
            self.configuration = QuicConfiguration(is_client=True, quic_logger=None)
        self.configuration.verify_mode = ssl.CERT_NONE
        self.hostip = host_addr
        self.portnr = port_nr
        self.quic_obj = self.create_quic_server_object()
        self.configuration.max_data= md
        self.configuration.max_stream_data=msd


    def create_quic_server_object(self):
        return quicconnect(self.hostip, self.portnr, configuration=self.configuration)


def randbytes(n,_struct8k=struct.Struct("!1000Q").pack_into):
    if n<8000:
        longs=(n+7)//8
        return struct.pack("!%iQ"%longs,*map(
            random.getrandbits,itertools.repeat(64,longs)))[:n]
    data=bytearray(n);
    for offset in range(0,n-7999,8000):
        _struct8k(data,offset,
            *map(random.getrandbits,itertools.repeat(64,1000)))
    offset+=8000
    data[offset:]=randbytes(n-offset)
    return data


import argparse

def parse(name):

    parser = argparse.ArgumentParser(description="Parser for Quic Client")


    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="The remote peer's host name or IP address",
    )

    parser.add_argument(
        "--port", type=int, default=4433, help="The remote peer's port number"
    )

    parser.add_argument(
        "-k",
        "--insecure",
        action="store_true",
        help="do not validate server certificate",
    )

    parser.add_argument(
        "--ca-certs", type=str, help="load CA certificates from the specified file"
    )

    parser.add_argument(
        "-q",
        "--quic-log",
        type=str,
        help="log QUIC events to QLOG files in the specified directory",
    )

    parser.add_argument(
        "-l",
        "--secrets-log",
        type=str,
        help="log secrets to a file, for use with Wireshark",
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="increase logging verbosity"
    )


    parser.add_argument(
        "--querysize",
        type=int,
        default=5000,
        help="Amount of data to send in bytes"
    )
    parser.add_argument(
        "--streamrange",
        type=int,
        default=100,
        help="no of times querysize data  wanted to send"
    )

    parser.add_argument(
        "--maxdata",
        type=int,
        default=1048576,
        help="connection-wide flow control limit (default: %d)" % QuicConfiguration.max_data,
    )
    parser.add_argument(
        "--maxstreamdata",
        type=int,
        default=1048576,
        help="per-stream flow control limit (default: %d)" % QuicConfiguration.max_stream_data,
    )

    args = parser.parse_args()

    return args

def main():
    print("Client Started")
    args = parse("Parse client args")
    test_data = []
    news=args.streamrange
    querysize=args.querysize
    if args.quic_log:
        from aioquic.quic import configuration
        from aioquic.quic.logger import QuicFileLogger
        configuration.quic_logger = QuicFileLogger(args.quic_log)
    if args.secrets_log:
        from aioquic.quic import configuration
        configuration.secrets_log_file = open(args.secrets_log, "a")
    if args.insecure:
        from aioquic.quic import configuration
        configuration.verify_mode = ssl.CERT_NONE

    for i in range(0,news):
        q = randbytes(n=querysize)
        test_data.append(q)
    print("sending test data size of " + str(int(str(sys.getsizeof(test_data[0])))/float(1<<20)) + " MB")
    k = quicconnectclient(args.host,args.port,args.verbose,args.maxdata,args.maxstreamdata,args.quic_log)
      
    for i in test_data:   
        #print(i)
        print("sending test data ",len(test_data)," times")
        k.quic_obj.send_frame(i)
        time.sleep(0.03)

    k.quic_obj.client_close()



if __name__ == "__main__":
    main()

