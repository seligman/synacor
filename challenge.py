#!/usr/bin/env python3

from command_opts import opt, main_entry
from program import Program
import zipfile
import os


@opt("Run example program")
def test():
    program = Program()
    program.load_string("9,32768,32769,4,19,32768")
    program.run()

@opt("Run the program")
def run():
    with zipfile.ZipFile(os.path.join("source", "challenge.zip"), 'r') as zip:
        machine = zip.read('challenge.bin')
    program = Program()
    program.load_bytes(machine)
    program.run()


@opt("Run the program from a saved state")
def load(filename):
    program = Program()
    program.deserialize(filename)
    program.run()


@opt("Run the program, looking for events")
def auto():
    with zipfile.ZipFile(os.path.join("source", "challenge.zip"), 'r') as zip:
        machine = zip.read('challenge.bin')
    program = Program()
    program.load_bytes(machine)
    program.deserialize(os.path.join("source", "start_state.zip"))
    # TODO
    program.run()


if __name__ == "__main__":
    main_entry('func')
