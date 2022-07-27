from queue import Queue
import asyncio
import logging
import ssl
import time
import threading
from aioquic.asyncio import QuicConnectionProtocol, serve
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.connection import QuicConnection
from aioquic.quic.events import QuicEvent, StreamDataReceived
from typing import Counter, Optional
import numpy as np

from aioquic.quic.logger import QuicFileLogger

logger = logging.getLogger("server")
dd = 0
total_data = bytes()
frame_data = []
send_time = 0
t2 = 0
offset = 0
index = 0
server_send_data = []
hist = []
average_offset = 0


class MyConnection:
    def __init__(self, quic: QuicConnection):
        self._quic = quic

    def handle_event(self, event: QuicEvent) -> None:
        global total_data, dd, send_time, t2, offset, index, server_send_data, hist, average_offset

        if isinstance(event, StreamDataReceived):
            data = event.data
            dd += 1
            if event.end_stream:
                dd = 0
                temp = dict()
                # print("offset",offset)
                if (len(hist) > 1):
                    k = np.average(hist[1:])
                    time_taken = time.time() - float(send_time) - k
                    temp["offset"] = k
                    # print("hist ",temp["offset"])
                else:
                    time_taken = time.time() - float(send_time) - float(offset)
                    temp["offset"] = float(offset)
                    # print("not hist ",temp["offset"])
                total_data += data
                temp["data"] = total_data
                temp["id"] = index
                temp["time_taken"] = time_taken
                temp["recv_time"] = time.time()
                frame_data.append(temp)
                total_data = bytes()
                ack = "frame " + str(index) + " recieved"
                self._quic.send_stream_data(event.stream_id, bytes(ack.encode()), True)
            elif (dd == 1):
                send_time, offset, index, data = data.decode('latin-1').split(",", 3)
                if (float(offset) != 0):
                    if (len(hist) > 1):
                        k = np.average(hist[1:])
                        if (abs(k) - abs(float(offset)) < 0.005):
                            hist.append(float(offset))
                    else:
                        hist.append(float(offset))
                t2 = str(time.time())
                data = data.encode()
                t3 = str(time.time())
                ts_data = t2 + "," + t3
                ts_data = ts_data.encode()
                self._quic.send_stream_data(event.stream_id, ts_data, False)
                total_data += data
            else:
                if (len(server_send_data) > 0):
                    sever_reply = server_send_data.pop(0)
                    if isinstance(sever_reply, str):
                        sever_reply = sever_reply.encode()
                    self._quic.send_stream_data(event.stream_id, sever_reply, False)


class MyServerProtocol(QuicConnectionProtocol):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._myConn: Optional[MyConnection] = None

    def quic_event_received(self, event: QuicEvent) -> None:
        # print("receieved a connection")
        # python QUIC_Server.py -c keys/RootCA.crt -k keys/RootCA.key
        self._myConn = MyConnection(self._quic)
        self._myConn.handle_event(event)


class quicserver(MyServerProtocol):
    def __init__(self, host, port, configuration):
        super().__init__(self)
        self.host = host
        self.port = port
        self.config = configuration
        self.server_start()

    def recieve(self):
        t1 = time.time()
        while True and (time.time() - t1) < 2:
            if (len(frame_data) > 0):
                t1 = time.time()
                temp = frame_data.pop(0)
                frame_ret = temp["data"]
                frame_time = temp["time_taken"]
                frame_index = temp["id"]
                fr_offset = temp["offset"]
                fr_recv = temp["recv_time"]
                return frame_index, frame_ret, frame_time, fr_offset, fr_recv
        return None, None, None, None, None

    def server_start(self):
        self.y = threading.Thread(target=self.quicrecieve)

        self.y.start()

    def server_send(self, data):
        global server_send_data
        server_send_data.append(data)

    def quicrecieve(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            serve(
                self.host,
                self.port,
                configuration=self.config,
                create_protocol=MyServerProtocol
            )
        )
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            exit()
            pass


class quicconnectserver():
    def __init__(self, host, port, certificate, private_key, verbose, qlog):
        logging.basicConfig(
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
            level=logging.DEBUG if verbose else logging.INFO, )
        if qlog:
            self.configuration = QuicConfiguration(is_client=False, quic_logger=QuicFileLogger(qlog))
        else:
            self.configuration = QuicConfiguration(is_client=False, quic_logger=None)
        self.configuration.load_cert_chain(certificate, private_key)
        self.configuration.verify_mode = ssl.CERT_NONE
        self.hostip = host
        self.portnr = port
        self.quic_obj = self.create_quic_server_object()

    def create_quic_server_object(self):
        return quicserver(self.hostip, self.portnr, configuration=self.configuration)


def processing(server,data_queue):
    
    time_start = time.time()
    
    while True:
        if data_queue and  time.time() - time_start < 10:
            
            frame = data_queue.get()
            t2 = time.time()
        
            if ( frame["time_taken"] + (t2 - frame["t1"]) < 0.15):
                #print("frame ",frame["id"]," processing")
                time.sleep(0.03)
                server_reply = frame["id"] + "processed"
                server.quic_obj.server_send(server_reply)
                time_start = time.time()
            else:
                #print("frame ",frame["id"]," dropped")
                server_reply = frame["id"] + "dropped"
                server.quic_obj.server_send(server_reply)





import argparse

def parse(name):

    parser = argparse.ArgumentParser(description=f"Parse args for the QUIC protocol")

    parser.add_argument(
        "--host",
        type=str,
        default="::",
        help="listen on the specified address (defaults to ::)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=4433,
        help="listen on the specified port (defaults to 4784)",
    )

    parser.add_argument(
        "-c",
        "--certificate",
        type=str,
        required=True,
        help="load the TLS certificate from the specified file",
    )

    parser.add_argument(
        "-k",
        "--private-key",
        type=str,
        help="load the TLS private key from the specified file",
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

    args = parser.parse_args()

    return args

def main():
    #print("entered server code")
    print("frame,time,offset,recv time")
    
    args = parse("Parse server args")
    if args.quic_log:
        quic_logger=args.quic_log

    # open SSL log file
    if args.secrets_log:
        secrets_log_file = open(args.secrets_log, "a")
    else:
        secrets_log_file = None

    data_queue = Queue()
    j = quicconnectserver(args.host,args.port,args.certificate, args.private_key,args.verbose,args.quic_log)
    prc_thread = threading.Thread(target=processing,args=(j,data_queue))
    prc_thread.start()
    counter = 0
    while True:
        id,f,t,o,r=j.quic_obj.recieve()
        if id:
            temp = dict()
            temp["frame"] = f
            temp["time_taken"] = t
            temp["t1"] = time.time()
            temp["id"] = id
            #print(id,",",t,",",o,",",r)
            #print("time",t)
            data_queue.put(temp)
            
        else:
            if counter > 10:
                exit()
            counter+=1
            
            

if __name__ == "__main__":
    main()

