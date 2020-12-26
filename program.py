#!/usr/bin/env python3

from collections import deque, defaultdict
from struct import unpack
from datetime import datetime

_opcodes = {"names": set()}


def opcode(name, opcode_num, size):
    def real_opts(func):
        if opcode_num in _opcodes:
            raise Exception(f"opcode {opcode_num} used more than once")
        if name in _opcodes['names']:
            raise Exception(f"name '{name}' used more than once")
        _opcodes['names'].add(name)
        _opcodes[opcode_num] = {
            'func': func,
            'name': name,
            'opcode': opcode_num,
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


@opcode("mult", 10, 4)
def op_mult(program, dest, a, b):
    value = (program.get_val(a) * program.get_val(b)) % 32768
    program.set_val(dest, value)


@opcode("mod", 11, 4)
def op_mod(program, dest, a, b):
    value = (program.get_val(a) % program.get_val(b))
    program.set_val(dest, value)


@opcode("rmem", 15, 3)
def op_rmem(program, dest, src):
    src = program.get_val(src)
    program.set_val(dest, program.memory[src])


@opcode("wmem", 16, 3)
def op_wmem(program, dest, src):
    src = program.get_val(src)
    dest = program.get_val(dest)
    program.memory[dest] = src


@opcode("out", 19, 2)
def op_out(program, value):
    value = program.get_val(value)
    if chr(value) == '\n':
        program.handle_io("   " + program.output_buffer)
        program.output_buffer = ""
    else:
        program.output_buffer += chr(value)
    print(chr(value), end='', flush=True)


@opcode("in", 20, 2)
def op_in(program, dest):
    if len(program.input_buffer) == 0:
        temp = input()
        temp = temp.strip()
        if temp in {"quit", "exit"}:
            raise ProgramException("Stopping at user request")
        temp += "\n"
        program.input_buffer += temp

    if program.input_buffer[0] == "\n":
        program.handle_io("+> " + program.input_buffer_echo)
        program.input_buffer_echo = ""
    else:
        program.input_buffer_echo += program.input_buffer[0]

    program.set_val(dest, ord(program.input_buffer[0]))
    program.input_buffer = program.input_buffer[1:]


@opcode("noop", 21, 1)
def op_noop(program):
    pass


@opcode("jmp", 6, 2)
def op_jmp(program, target):
    target = program.get_val(target)
    program.pc = target


@opcode("call", 17, 2)
def op_call(program, target):
    target = program.get_val(target)
    program.stack.append(program.pc)
    program.pc = target


@opcode("ret", 18, 1)
def op_ret(program):
    target = program.stack.pop()
    program.pc = target


@opcode("jt", 7, 3)
def op_jt(program, value, target):
    target = program.get_val(target)
    value = program.get_val(value)
    if value != 0:
        program.pc = target


@opcode("jf", 8, 3)
def op_jf(program, value, target):
    target = program.get_val(target)
    value = program.get_val(value)
    if value == 0:
        program.pc = target


@opcode("set", 1, 3)
def op_set(program, dest, value):
    value = program.get_val(value)
    program.set_val(dest, value)


@opcode("eq", 4, 4)
def op_eq(program, dest, a, b):
    a = program.get_val(a)
    b = program.get_val(b)
    program.set_val(dest, 1 if a == b else 0)


@opcode("gt", 5, 4)
def op_gt(program, dest, a, b):
    a = program.get_val(a)
    b = program.get_val(b)
    program.set_val(dest, 1 if a > b else 0)


@opcode("and", 12, 4)
def op_and(program, dest, a, b):
    a = program.get_val(a)
    b = program.get_val(b)
    program.set_val(dest, a & b)


@opcode("or", 13, 4)
def op_or(program, dest, a, b):
    a = program.get_val(a)
    b = program.get_val(b)
    program.set_val(dest, a | b)


@opcode("not", 14, 3)
def op_not(program, dest, a):
    a = program.get_val(a)
    program.set_val(dest, a ^ 32767)


@opcode("push", 2, 2)
def op_push(program, value):
    value = program.get_val(value)
    program.stack.append(value)


@opcode("pop", 3, 2)
def op_pop(program, dest):
    program.set_val(dest, program.stack.pop())


class Program:
    def __init__(self):
        self.pc = 0
        self.memory = {}
        self.registers = [0] * 8
        self.stack = deque()
        self.input_buffer = ""
        self.input_buffer_echo = ""
        self.output_buffer = ""

        self.handle_io("----- Program Log for " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " -----")
        self.handle_io("")

    def handle_io(self, value):
        with open("program.log", "a") as f:
            f.write(value + "\n")

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
                    raise ProgramException(f"Unknown opcode: {opcode}")
                opcode = _opcodes[opcode]
                args = [self]
                for i in range(1, opcode['size']):
                    args.append(self.memory[self.pc + i])
                self.pc += opcode['size']
                opcode['func'](*args)
        except ProgramException as msg:
            print(f"Status: {msg.msg}")
