#!/usr/bin/env python3

from command_opts import opt, main_entry
from program import Program
import zipfile
import os


@opt("Hello, world")
def hello():
    print("This is a hello, world example")


@opt("Run example program")
def test():
    program = Program()
    program.load_string("9,32768,32769,4,19,32768")
    program.run()

@opt("Run the program")
def run():
    zip = zipfile.ZipFile(os.path.join("source", "challenge.zip"), 'r')
    machine = zip.read('challenge.bin')
    program = Program()
    program.load_bytes(machine)
    program.run()


if __name__ == "__main__":
    main_entry('func')
