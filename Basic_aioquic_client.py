############ BASIC CLIENT ##################
import argparse
import asyncio
import ssl
import struct

import aioquic.asyncio
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import StreamDataReceived

_I = struct.Struct('!I')


class QuicClient(aioquic.asyncio.QuicConnectionProtocol):

    def quic_event_received(self, quic_event):
        if isinstance(quic_event, StreamDataReceived):
            if quic_event.end_stream:
                self.time.set_result(self._loop.time() - self.start_time)

    def transfer(self, size):
        self._quic.send_stream_data(
            stream_id=self._quic.get_next_available_stream_id(),
            data=_I.pack(size),
            end_stream=True,
        )
        self.transmit()
        self.start_time = self._loop.time()
        self.time = self._loop.create_future()
        return self.time


async def main(host='172.16.2.1', port=9999, size=1048576):
    async with aioquic.asyncio.connect(
        host, port,
        configuration=QuicConfiguration(verify_mode=ssl.CERT_NONE),
        create_protocol=QuicClient,
    ) as client:
        print('Transfer speed: {:.3f} Mbps'.format(
            size * 8 / 1000 / 1000 / await client.transfer(size))
        )


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('size', nargs='?', type=int, default=64, help='Transfer size (MiB)')
    args = parser.parse_args()
    asyncio.run(
        main(
            size=args.size * 1048576,
        )
    )


