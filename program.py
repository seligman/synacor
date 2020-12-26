#!/usr/bin/env python3

from collections import deque, defaultdict
from struct import unpack

_opcodes = {}

def opcode(name, value, size):
    def real_opts(func):
        _opcodes[value] = {
            'func': func,
            'name': name,
            'opcode': value,
            'size': size,
        }
        def wrapper(*args2, **kwargs):
            return func(*args2, **kwargs)
        return wrapper
    return real_opts


class ProgramException(BaseException):
    def __init__(self, msg):
        self.msg = msg


@opcode("halt", 0, 1)
def op_halt(program):
    raise ProgramException("Halt instruction hit!")


@opcode("add", 9, 4)
def op_add(program, dest, a, b):
    value = (program.get_val(a) + program.get_val(b)) % 32768
    program.set_val(dest, value)


@opcode("out", 19, 2)
def op_out(program, value):
    value = program.get_val(value)
    print(chr(value), end='', flush=True)


@opcode("noop", 21, 1)
def op_noop(program):
    pass


class Program:
    def __init__(self):
        self.pc = 0
        self.memory = {}
        self.registers = [0] * 8
        self.stack = deque()

    def load_string(self, value):
        values = [int(x) for x in value.split(',')]
        for i in range(len(values)):
            self.memory[i] = values[i]

    def load_bytes(self, value):
        for i in range(0, len(value), 2):
            self.memory[i // 2] = unpack('<H', value[i:i+2])[0]

    def get_val(self, value):
        if value < 32768:
            return value
        else:
            return self.registers[value - 32768]

    def set_val(self, dest, value):
        if dest < 32768:
            raise Exception()
        else:
            self.registers[dest - 32768] = value

    def run(self):
        try:
            while True:
                if self.pc not in self.memory:
                    raise ProgramException("End of program")
                opcode = self.memory[self.pc]
                if opcode not in _opcodes:
                    raise ProgramException("Unknown opcode: " + str(opcode))
                opcode = _opcodes[opcode]
                args = [self]
                for i in range(1, opcode['size']):
                    args.append(self.memory[self.pc + i])
                self.pc += opcode['size']
                opcode['func'](*args)
        except ProgramException as msg:
            print("Status: " + msg.msg)
