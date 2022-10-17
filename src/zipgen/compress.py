from asyncio import get_running_loop
from io import BufferedIOBase
from zlib import compressobj, crc32
from bz2 import BZ2Compressor
from lzma import LZMACompressor, FORMAT_RAW
from typing import AsyncGenerator, Generator, Optional, Union, cast

from .constant import COMPRESSION_STORED, COMPRESSION_DEFLATED, COMPRESSION_BZIP2, COMPRESSION_LZMA, CREATE_BZIP2, CREATE_DEFAULT, CREATE_LZMA, CREATE_ZIP64


__all__ = (
    "CompressorBase",
    "CompressorStored",
    "CompressorDeflated",
    "CompressorBZ2",
    "CompressorLZMA",
    "get_compressor",
    "get_extract_version",
    "CompressorContext",
    "compress_gen",
    "compress_gen_async",
)


class CompressorBase(object):
    __slots__ = ()

    def compress(self, data: bytes) -> bytes:
        """Abstract compress method."""
        raise NotImplementedError

    def flush(self) -> bytes:
        """Abstract flush method."""
        raise NotImplementedError


class CompressorStored(CompressorBase):
    __slots__ = ()

    def compress(self, data: bytes) -> bytes:
        """Returns data unmodified."""
        return bytes(data)

    def flush(self) -> bytes:
        """Returns empty buffer."""
        return b""


class CompressorDeflated(CompressorBase):
    __slots__ = ("compressor",)

    def __init__(self) -> None:
        self.compressor = compressobj(-1, 8, -15)

    def compress(self, data: bytes) -> bytes:
        """Returns deflate compressed data."""
        return self.compressor.compress(data)

    def flush(self) -> bytes:
        """Returns remaning data."""
        return self.compressor.flush()


class CompressorBZ2(CompressorBase):
    __slots__ = ("compressor",)

    def __init__(self) -> None:
        self.compressor = BZ2Compressor()

    def compress(self, data: bytes) -> bytes:
        """Returns BZIP2 compressed data."""
        return self.compressor.compress(data)

    def flush(self) -> bytes:
        """Returns remaning data."""
        return self.compressor.flush()


class CompressorLZMA(CompressorBase):
    __slots__ = ("compressor",)

    def __init__(self) -> None:
        self.compressor: Optional[LZMACompressor] = None

    def _init(self) -> bytes:
        """Initializes compressor with encode and decode props."""
        self.compressor = LZMACompressor(FORMAT_RAW, filters=[
            {"id": 4611686018427387905, "lc": 3,
             "lp": 0, "pb": 2, "dict_size": 8388608}
        ])

        return b"\t\x04\x05\x00]\x00\x00\x80\x00"

    def compress(self, data: bytes) -> bytes:
        """Returns LZMA compressed data."""
        if self.compressor is None:
            return self._init() + cast(LZMACompressor, self.compressor).compress(data)
        return self.compressor.compress(data)

    def flush(self) -> bytes:
        """Returns remaning data."""
        if self.compressor is None:
            return self._init() + cast(LZMACompressor, self.compressor).flush()
        return self.compressor.flush()


def get_compressor(compression: int) -> CompressorBase:
    """Returns equivalent compressor."""
    if compression == COMPRESSION_STORED:
        return CompressorStored()
    elif compression == COMPRESSION_DEFLATED:
        return CompressorDeflated()
    elif compression == COMPRESSION_BZIP2:
        return CompressorBZ2()
    elif compression == COMPRESSION_LZMA:
        return CompressorLZMA()
    else:
        raise NotImplementedError("Compression not implemented.")


def get_extract_version(compression: int, zip64: bool) -> int:
    """Returns minimium required extract version."""
    if compression == COMPRESSION_LZMA:
        return CREATE_LZMA
    elif compression == COMPRESSION_BZIP2:
        return CREATE_BZIP2
    elif zip64:
        return CREATE_ZIP64

    return CREATE_DEFAULT


class CompressorContext(object):
    __slots__ = (
        "crc32",
        "compressed_size",
        "uncompressed_size",
    )

    def __init__(self) -> None:
        self.crc32 = 0
        self.compressed_size = 0
        self.uncompressed_size = 0

    def update(self, rbuf: bytes, cbuf: bytes) -> None:
        """Updates context values."""
        self.crc32 = crc32(rbuf, self.crc32) & 0xFFFFFFFF
        self.compressed_size += len(cbuf)
        self.uncompressed_size += len(rbuf)

    def flush(self, buf: bytes) -> None:
        """Update compressed size with flushed buffer."""
        self.compressed_size += len(buf)


def compress_gen(compressor: CompressorBase, context: CompressorContext, io: BufferedIOBase, buffer: Union[memoryview, bytearray]) -> Generator[bytes, None, None]:
    """Compresses, updates context and yields compressed data."""
    while True:
        count = io.readinto(buffer)
        if count <= 0:
            break

        rbuf = buffer[:count]
        cbuf = compressor.compress(rbuf)
        context.update(rbuf, cbuf)

        yield cbuf

    # Flush
    buf = compressor.flush()

    # Yield remaining
    if len(buf) != 0:
        context.flush(buf)
        yield buf


async def compress_gen_async(compressor: CompressorBase, context: CompressorContext, io: BufferedIOBase, buffer: Union[memoryview, bytearray]) -> AsyncGenerator[bytes, None]:
    """Compresses, updates context and yields compressed asynchronously."""
    loop = get_running_loop()
    gen = compress_gen(compressor, context, io, buffer)

    def try_get_next() -> Optional[bytes]:
        try:
            return gen.__next__()
        except StopIteration:
            return None

    while True:
        buf = await loop.run_in_executor(None, try_get_next)
        if buf is None:
            break
        yield buf
