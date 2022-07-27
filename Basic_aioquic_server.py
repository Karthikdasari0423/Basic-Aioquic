
######################BASIC SERVER ####################




import argparse
import asyncio
import struct

import aioquic.asyncio
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import StreamDataReceived

_I = struct.Struct('!I')


class QuicServer(aioquic.asyncio.QuicConnectionProtocol):

    def quic_event_received(self, quic_event):
        if isinstance(quic_event, StreamDataReceived):
            size, = _I.unpack(quic_event.data)
            self._quic.send_stream_data(
                stream_id=quic_event.stream_id,
                data=b'\x00' * size,
                end_stream=True,
            )
            self.transmit()


async def main(certfile, keyfile=None, password=None, host='172.16.2.1', port=9999):
    configuration = QuicConfiguration(is_client=False)
    configuration.load_cert_chain(certfile=certfile, keyfile=keyfile, password=password)
    server = await aioquic.asyncio.serve(
        host, port,
        configuration=configuration,
        create_protocol=QuicServer,
    )

    loop = asyncio.get_running_loop()
    try:
        await loop.create_future()
    finally:
        server.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--certificate', required=True)
    parser.add_argument('-k', '--private-key')
    args = parser.parse_args()
    asyncio.run(
        main(
            certfile=args.certificate,
            keyfile=args.private_key,
        )
    )


