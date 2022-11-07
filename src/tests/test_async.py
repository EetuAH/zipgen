from asyncio import subprocess, sleep
from typing import AsyncGenerator
from unittest import IsolatedAsyncioTestCase, main
from io import BytesIO
from zipfile import ZipFile
from zipgen import ZipBuilder


class TestSync(IsolatedAsyncioTestCase):
    async def test_stream_async(self) -> None:
        """Test stream generator."""
        builder = ZipBuilder()
        io = BytesIO()
        args = b"hello world"

        # Read process content to zip
        proc = await subprocess.create_subprocess_exec(
            "echo", args,
            stdout=subprocess.PIPE,
        )

        if proc.stdout is not None:
            async for buf in builder.add_stream_async("echo.txt", proc.stdout):
                io.write(buf)

        # End
        io.write(builder.end())

        # Check existence
        with ZipFile(io, "r") as file:
            self.assertEqual(
                file.namelist(),
                ["echo.txt"],
            )

            for name in file.namelist():
                self.assertTrue(file.read(name).startswith(args))

    async def test_walk_async(self) -> None:
        """Test walk generator."""
        builder = ZipBuilder()
        io = BytesIO()

        # Walk tests files
        async for buf in builder.walk_async("./", "/"):
            io.write(buf)

        # End
        io.write(builder.end())

        # Check existence
        with ZipFile(io, "r") as file:
            self.assertEqual(
                file.namelist(),
                ["test_sync.py", "test_async.py"],
            )

            for name in file.namelist():
                self.assertNotEqual(len(file.read(name)), 0)

    async def test_gen_async(self) -> None:
        """Test async generator."""
        builder = ZipBuilder()
        io = BytesIO()

        # Contents for AsyncGenerator
        data = (b"hello", b"world", b"from", b"AsyncGenerator", b"x"*1024)

        # AsyncGenerator for data
        async def gen_data_async() -> AsyncGenerator[bytes, None]:
            for buf in data:
                await sleep(0)
                yield buf

        # Write generator content to io
        async for buf in builder.add_gen_async("gen.txt", gen_data_async()):
            io.write(buf)

        # End
        io.write(builder.end())

        # Check existence
        with ZipFile(io, "r") as file:
            self.assertEqual(
                file.namelist(),
                ["gen.txt"],
            )

            for name in file.namelist():
                self.assertEqual(file.read(name), b"".join(data))


if __name__ == "__main__":
    main()
