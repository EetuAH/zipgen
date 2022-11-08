from typing import Generator
from unittest import TestCase, main
from io import BytesIO
from sys import argv
from os import listdir
from os.path import dirname
from zipfile import ZipFile
from zipgen import ZipStreamWriter, COMPRESSION_STORED, COMPRESSION_DEFLATED, COMPRESSION_BZIP2, COMPRESSION_LZMA


print(argv[0], dirname(argv[0]))


class TestStreamSync(TestCase):
    def test_add_file(self) -> None:
        """Tests file creation."""
        io = BytesIO()
        stream = ZipStreamWriter(io)

        # Contents
        content1 = b"This is COMPRESSION_STORED compressed. " * 128
        content2 = b"This is COMPRESSION_DEFLATED compressed. " * 128
        content3 = b"This is COMPRESSION_BZIP2 compressed. " * 128
        content4 = b"This is COMPRESSION_LZMA compressed. " * 128

        # Add four files with different compressions
        stream.add_io("file1.txt", BytesIO(content1),
                      compression=COMPRESSION_STORED)
        stream.add_io("file2.txt", BytesIO(content2),
                      compression=COMPRESSION_DEFLATED)
        stream.add_io("file3.txt", BytesIO(content3),
                      compression=COMPRESSION_BZIP2)
        stream.add_io("file4.txt", BytesIO(content4),
                      compression=COMPRESSION_LZMA)

        # End
        stream.end()

        # Check existence
        with ZipFile(io, "r") as file:
            self.assertEqual(
                file.namelist(),
                ["file1.txt", "file2.txt", "file3.txt", "file4.txt"],
            )

            self.assertEqual(file.read("file1.txt"), content1)
            self.assertEqual(file.read("file2.txt"), content2)
            self.assertEqual(file.read("file3.txt"), content3)
            self.assertEqual(file.read("file4.txt"), content4)

    def test_add_folder(self) -> None:
        """Test folder creation."""
        io = BytesIO()

        with ZipStreamWriter(io) as stream:
            # Add three folders
            stream.add_folder("test1")
            stream.add_folder("test1/test2")
            stream.add_folder("test1/test2/test3")

        # Check existence
        with ZipFile(io, "r") as file:
            self.assertEqual(
                file.namelist(),
                ["test1/", "test1/test2/", "test1/test2/test3/"],
            )

    def test_add_buf(self) -> None:
        """Test adding buffers."""
        io = BytesIO()

        # Datas
        data1 = b"hello from buf1.txt"
        data2 = bytearray(b"hello from buf2.txt")
        data3 = memoryview(b"hello from buf3.txt")

        with ZipStreamWriter(io) as stream:
            # Add three buffers
            stream.add_buf("buf1.txt", data1)
            stream.add_buf("buf2.txt", data2)
            stream.add_buf("buf3.txt", data3)

        # Check existence
        with ZipFile(io, "r") as file:
            self.assertEqual(
                file.namelist(),
                ["buf1.txt", "buf2.txt", "buf3.txt"],
            )

            self.assertEqual(file.read("buf1.txt"), data1)
            self.assertEqual(file.read("buf2.txt"), data2)
            self.assertEqual(file.read("buf3.txt"), data3)

    def test_walk(self) -> None:
        """Test walk generator."""
        io = BytesIO()
        path = dirname(argv[0])

        with ZipStreamWriter(io) as stream:
            # Walk tests files
            stream.walk(path, "/")

        # Check existence
        with ZipFile(io, "r") as file:
            self.assertEqual(
                file.namelist(),
                listdir(path),
            )

            for name in file.namelist():
                self.assertNotEqual(len(file.read(name)), 0)

    def test_gen(self) -> None:
        """Test async generator."""
        io = BytesIO()

        # Contents for Generator
        data = (b"hello", b"world", b"from", b"Generator", b"x"*1024)

        with ZipStreamWriter(io) as stream:
            # Generator for data
            def gen_data() -> Generator[bytes, None, None]:
                for buf in data:
                    yield buf

            # Write generator content to io
            stream.add_gen("async_gen.txt", gen_data())

            # Check existence
        with ZipFile(io, "r") as file:
            self.assertEqual(
                file.namelist(),
                ["async_gen.txt"],
            )

            for name in file.namelist():
                self.assertEqual(file.read(name), b"".join(data))


if __name__ == "__main__":
    main()
