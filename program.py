#!/usr/bin/env python3

from collections import deque, defaultdict
from struct import unpack, pack
from datetime import datetime
from inspect import signature
import zipfile

_opcodes = {"names": {}}
_io_logger = None


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
    if program.log_reads:
        program.show(f">> Memory read {src} > {program.memory[src]}")
    program.set_val(dest, program.memory[src])


@opcode("wmem", 16)
def op_wmem(program, dest, src):
    src = program.get_val(src)
    dest = program.get_val(dest)
    program.memory[dest] = src
    program.changed[dest] = src


@opcode("out", 19)
def op_out(program, value):
    if "bpo" in program.breakpoints:
        if program.output_buffer == "":
            program.breakpoint()
    value = program.get_val(value)
    valid = True
    if value < 32 and value != 10:
        valid = False
    if value >= 127:
        valid = False
    if not valid:
        raise ProgramException("Unknown output character")
    if _io_logger:
        _io_logger.handle_output(program, chr(value))
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


def debugger(program, value):
    if value == "?":
        print("bpo      = Break on output")
        print("bpr #    = Break on a read of register #x")
        print("setr r # = Set register r to #")
        print("dump     = Decompile code")
        print("inv #    = Invert the meaning of #")
        print("jmp #    = Jump to a PC")
        print("noop #   = Noop an instruction")
        return True
    if value.startswith("noop "):
        program.memory[int(value[5:])] = 21
        print("noop set")
        return True
    if value.startswith("jmp "):
        program.pc = int(value[4:])
        print("PC set")
        return True
    if value.startswith("inv "):
        program.breakpoints.add(value)
        print("Inverted meaning added")
        return True
    if value.startswith("bpr "):
        program.breakpoints.add(value)
        print("Breakpoint added")
        return True
    if value.startswith("bpo"):
        program.breakpoints.add(value)
        print("Breakpoint added")
        return True
    if value.startswith("setr"):
        value = value.split(' ')
        program.registers[int(value[1])] = int(value[2])
        print(f"Register {value[1]} set to {value[2]}")
        return True
    if value.startswith("dump"):
        program.dump("decompiled.txt")
        print("Program decompiled")
        return True
    return False


@opcode("in", 20)
def op_in(program, dest):
    if len(program.input_buffer) == 0:
        program.room = []
        temp = ""
        while len(temp) == 0:
            temp = input()
            temp = temp.strip()
            if temp in {"quit", "exit"}:
                raise ProgramException("Stopping at user request")
            if temp in {"save"}:
                program.save_state.serialize("temp.zip")
                raise ProgramException("Program state saved")
            if debugger(program, temp):
                print("? ", end="", flush=True)
                temp = ""
        temp += "\n"
        program.input_buffer += temp

    if program.input_buffer[0] == "\n":
        program.handle_io("+> " + program.input_buffer_echo)
        program.input_buffer_echo = ""
    else:
        program.input_buffer_echo += program.input_buffer[0]

    if _io_logger:
        _io_logger.handle_input(program, program.input_buffer[0])
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
    if f"inv {program.history[-1]}" in program.breakpoints:
        print(f"Invert logic hit for {program.history[-1]}")
        if value == 0:
            program.pc = target
    else:
        if value != 0:
            program.pc = target


@opcode("jf", 8)
def op_jf(program, value, target):
    target = program.get_val(target)
    value = program.get_val(value)
    if f"inv {program.history[-1]}" in program.breakpoints:
        print(f"Invert logic hit for {program.history[-1]}")
        if value != 0:
            program.pc = target
    else:
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
    @staticmethod
    def set_logger(logger):
        global _io_logger
        _io_logger = logger

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

        self.need_header = True
        self.save_state = None
        self.hide_output = False
        self.log_all = False
        self.log_reads = False
        self.breakpoints = set()
        self.history = deque()

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
        if self.need_header:
            self.need_header = False
            self.handle_io("----- Program Log for " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " -----")
            self.handle_io("")
        with open("program.log", "a") as f:
            f.write(value + "\n")

    def show(self, value, input=False):
        if _io_logger:
            if input:
                [_io_logger.handle_input(self, x) for x in value + "\n"]
            else:
                [_io_logger.handle_output(self, x) for x in value + "\n"]
        print(value)
        self.handle_io(value)

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
            if f"bpr {value - 32768}" in self.breakpoints:
                self.breakpoint()
            if self.log_reads:
                self.show(f">> Register read {value - 32768} > {self.registers[value - 32768]}")
            return self.registers[value - 32768]

    def decode(self, pc):
        if self.memory[pc] in _opcodes:
            op = _opcodes[self.memory[pc]]
            info = f"{pc:5d}: {op['name']:<4}"
            pc += 1
            for _ in range(op['size']-1):
                if self.memory[pc] < 32768:
                    info += f" {self.memory[pc]}"
                else:
                    info += f" [{self.memory[pc] - 32768}]"
                pc += 1
        else:
            info = f"{pc:5d}: {self.memory[pc]}"
            pc += 1
        return pc, info

    def dump(self, filename):
        with open(filename, "w") as f:
            pc = 0
            while pc < len(self.memory):
                pc, info = self.decode(pc)
                f.write(info + "\n")

    def breakpoint(self):
        print(self.registers)
        temp = self.history.copy()
        for _ in range(20):
            if len(temp) > 0:
                pc = temp.popleft()
            if self.memory[pc] in _opcodes:
                op = _opcodes[self.memory[pc]]
                info = f"{'>' if pc == self.history[-1] else ' '} {pc:5d}: {op['name']:<4}"
                pc += 1
                for _ in range(op['size']-1):
                    if self.memory[pc] < 32768:
                        info += f" {self.memory[pc]}"
                    else:
                        info += f" [{self.memory[pc] - 32768}]"
                    pc += 1
            else:
                info = f"{pc:5d}: {self.memory[pc]}"
                pc += 1
            pc, info = self.decode(pc)

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
                if self.log_all:
                    _, info = self.decode(self.pc)
                    self.handle_io(info)
                self.history.append(self.pc)
                while len(self.history) > 5:
                    self.history.popleft()
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
            return "Done"
        except ProgramException as msg:
            if not self.hide_output:
                if len(self.output_buffer) > 0:
                    print("", flush=True)
                print(f"ERROR: {msg.msg}")
                self.handle_io(f"ERROR: {msg.msg}")
            return msg.msg
