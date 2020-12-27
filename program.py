#!/usr/bin/env python3

from collections import deque, defaultdict
from struct import unpack, pack
from datetime import datetime
from inspect import signature
import zipfile

_opcodes = {"names": {}}


def opcode(name, opcode_num):
    def real_opts(func):
        if opcode_num in _opcodes:
            raise Exception(f"opcode {opcode_num} used more than once")
        if name in _opcodes['names']:
            raise Exception(f"name '{name}' used more than once")
        _opcodes['names'][name] = opcode_num
        _opcodes[opcode_num] = {
            'func': func,
            'name': name,
            'opcode': opcode_num,
            'size': len(signature(func).parameters),
        }
        def wrapper(*args2, **kwargs):
            return func(*args2, **kwargs)
        return wrapper
    return real_opts


class ProgramException(BaseException):
    def __init__(self, msg):
        self.msg = msg


@opcode("halt", 0)
def op_halt(program):
    raise ProgramException("Halt instruction hit!")


@opcode("add", 9)
def op_add(program, dest, a, b):
    value = (program.get_val(a) + program.get_val(b)) % 32768
    program.set_val(dest, value)


@opcode("mult", 10)
def op_mult(program, dest, a, b):
    value = (program.get_val(a) * program.get_val(b)) % 32768
    program.set_val(dest, value)


@opcode("mod", 11)
def op_mod(program, dest, a, b):
    value = (program.get_val(a) % program.get_val(b))
    program.set_val(dest, value)


@opcode("rmem", 15)
def op_rmem(program, dest, src):
    src = program.get_val(src)
    program.set_val(dest, program.memory[src])


@opcode("wmem", 16)
def op_wmem(program, dest, src):
    src = program.get_val(src)
    dest = program.get_val(dest)
    program.memory[dest] = src
    program.changed[dest] = src


@opcode("out", 19)
def op_out(program, value):
    value = program.get_val(value)
    if value < 32 and value != ord('\n'):
        value = "\\x%02X" % (value,)
    else:
        value = chr(value)
    if value == '\n':
        program.room.append(program.output_buffer)
        program.handle_io("   " + program.output_buffer)
        program.output_buffer = ""
    else:
        program.output_buffer += value
    if not program.hide_output:
        print(value, end='', flush=True)


@opcode("in", 20)
def op_in(program, dest):
    if len(program.input_buffer) == 0:
        program.room = []
        temp = input()
        temp = temp.strip()
        if temp in {"quit", "exit"}:
            raise ProgramException("Stopping at user request")
        if temp in {"save"}:
            program.save_state.serialize("temp.zip")
            raise ProgramException("Program state saved")
        temp += "\n"
        program.input_buffer += temp

    if program.input_buffer[0] == "\n":
        program.handle_io("+> " + program.input_buffer_echo)
        program.input_buffer_echo = ""
    else:
        program.input_buffer_echo += program.input_buffer[0]

    program.set_val(dest, ord(program.input_buffer[0]))
    program.input_buffer = program.input_buffer[1:]

    if len(program.input_buffer) == 0:
        program.save_state = program.clone()


@opcode("noop", 21)
def op_noop(program):
    pass


@opcode("jmp", 6)
def op_jmp(program, target):
    target = program.get_val(target)
    program.pc = target


@opcode("call", 17)
def op_call(program, target):
    target = program.get_val(target)
    program.stack.append(program.pc)
    program.pc = target


@opcode("ret", 18)
def op_ret(program):
    target = program.stack.pop()
    program.pc = target


@opcode("jt", 7)
def op_jt(program, value, target):
    target = program.get_val(target)
    value = program.get_val(value)
    if value != 0:
        program.pc = target


@opcode("jf", 8)
def op_jf(program, value, target):
    target = program.get_val(target)
    value = program.get_val(value)
    if value == 0:
        program.pc = target


@opcode("set", 1)
def op_set(program, dest, value):
    value = program.get_val(value)
    program.set_val(dest, value)


@opcode("eq", 4)
def op_eq(program, dest, a, b):
    a = program.get_val(a)
    b = program.get_val(b)
    program.set_val(dest, 1 if a == b else 0)


@opcode("gt", 5)
def op_gt(program, dest, a, b):
    a = program.get_val(a)
    b = program.get_val(b)
    program.set_val(dest, 1 if a > b else 0)


@opcode("and", 12)
def op_and(program, dest, a, b):
    a = program.get_val(a)
    b = program.get_val(b)
    program.set_val(dest, a & b)


@opcode("or", 13)
def op_or(program, dest, a, b):
    a = program.get_val(a)
    b = program.get_val(b)
    program.set_val(dest, a | b)


@opcode("not", 14)
def op_not(program, dest, a):
    a = program.get_val(a)
    program.set_val(dest, a ^ 32767)


@opcode("push", 2)
def op_push(program, value):
    value = program.get_val(value)
    program.stack.append(value)


@opcode("pop", 3)
def op_pop(program, dest):
    program.set_val(dest, program.stack.pop())


class Serialize:
    def __init__(self):
        self.buffer = []
        self.offset = 0

    def read_int(self):
        ret = unpack("<H", self.buffer[self.offset:self.offset+2])[0]
        self.offset += 2
        return ret

    def read_list(self):
        ret = []
        count = self.read_int()
        for _ in range(count):
            ret.append(self.read_int())
        return ret

    def read_str(self):
        count = self.read_int()
        ret = self.buffer[self.offset:self.offset+count].decode("utf-8")
        self.offset += count
        return ret

    def add_int(self, value):
        self.buffer.append(pack('<H', value))

    def add_list(self, value):
        self.add_int(len(value))
        for cur in value:
            self.add_int(cur)

    def add_str(self, value):
        value = value.encode("utf-8")
        self.add_int(len(value))
        self.buffer.append(value)

class Program:
    def __init__(self):
        self.pc = 0
        self.memory = []
        self.changed = {}
        self.registers = [0] * 8
        self.stack = deque()
        self.input_buffer = ""
        self.input_buffer_echo = ""
        self.output_buffer = ""
        self.room = []

        self.save_state = None
        self.hide_output = False

        self.handle_io("----- Program Log for " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " -----")
        self.handle_io("")

    def clone(self):
        ret = Program()
        ret.pc = self.pc
        ret.memory = self.memory[:]
        ret.changed = self.changed.copy()
        ret.registers = self.registers[:]
        ret.stack = self.stack.copy()
        ret.input_buffer = self.input_buffer
        ret.input_buffer_echo = self.input_buffer_echo
        ret.output_buffer = self.output_buffer
        return ret

    def deserialize(self, filename):
        data = Serialize()
        with zipfile.ZipFile(filename, 'r') as zip:
            data.buffer = zip.read('state.bin')
        self.pc = data.read_int()
        self.registers = data.read_list()
        self.stack = deque(data.read_list())
        keys = data.read_list()
        values = data.read_list()
        self.changed = {keys[x]: values[x] for x in range(len(keys))}
        for key, value in self.changed.items():
            self.memory[key] = value
        self.input_buffer = data.read_str()
        self.input_buffer_echo = data.read_str()
        self.output_buffer = data.read_str()

    def serialize(self, filename):
        data = Serialize()
        data.add_int(self.pc)
        data.add_list(self.registers)
        data.add_list(self.stack)
        data.add_list(self.changed.keys())
        data.add_list(self.changed.values())
        data.add_str(self.input_buffer)
        data.add_str(self.input_buffer_echo)
        data.add_str(self.output_buffer)
        with zipfile.ZipFile(filename, 'w', compression=zipfile.ZIP_BZIP2, compresslevel=9) as zip:
            zip.writestr('state.bin', b''.join(data.buffer))

    def handle_io(self, value):
        with open("program.log", "a") as f:
            f.write(value + "\n")

    def load_string(self, value):
        self.memory = [int(x) for x in value.split(',')]
        self.changed = {}

    def load_bytes(self, value):
        self.memory = list(unpack('<' + 'H' * (len(value) // 2), value))
        self.changed = {}

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

    def run(self, abort_on_input=False, hide_output=False):
        self.hide_output = hide_output
        try:
            while True:
                if self.pc >= len(self.memory):
                    raise ProgramException("End of program")
                opcode = self.memory[self.pc]
                if abort_on_input and len(self.input_buffer) == 0:
                    if opcode == _opcodes['names']['in']:
                        return
                if opcode not in _opcodes:
                    raise ProgramException(f"Unknown opcode: {opcode}")
                opcode = _opcodes[opcode]
                args = [self]
                for i in range(1, opcode['size']):
                    args.append(self.memory[self.pc + i])
                self.pc += opcode['size']
                opcode['func'](*args)
        except ProgramException as msg:
            if not self.hide_output:
                if len(self.output_buffer) > 0:
                    print("", flush=True)
                print(f"Status: {msg.msg}")
