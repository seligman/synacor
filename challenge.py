#!/usr/bin/env python3

from command_opts import opt, main_entry
from program import Program, _opcodes
import zipfile
import os
import re
import json
from collections import deque

@opt("Run example program")
def test():
    program = Program()
    program.load_string("9,32768,32769,4,19,32768")
    program.run()


@opt("Run the program, showing memory changes")
def run_mem(savedstate=""):
    with zipfile.ZipFile(os.path.join("source", "challenge.zip"), 'r') as zip:
        machine = zip.read('challenge.bin')
    program = Program()
    program.load_bytes(machine)
    show_all = False
    if len(savedstate):
        program.deserialize(savedstate)
    memory = []
    while True:
        program.run(abort_on_input=True)
        if len(memory) == 0:
            memory = program.memory[:]
        else:
            for i in range(len(memory)):
                if memory[i] != program.memory[i]:
                    if show_all or i == 2732:
                        print(f"{i} => {memory[i]} != {program.memory[i]}")
        temp = input("Step? ")
        if temp.startswith("all"):
            show_all = not show_all
        elif temp.startswith("room "):
            temp = temp[4:]
            program.memory[2732] = int(temp)
        elif temp.startswith("mem "):
            temp = temp[4:].split(' ')
            program.memory[int(temp[0])] = int(temp[1])
        elif temp == "reset":
            memory = program.memory[:]
        else:
            program.input_buffer += temp + "\n"


@opt("Run the program")
def run():
    with zipfile.ZipFile(os.path.join("source", "challenge.zip"), 'r') as zip:
        machine = zip.read('challenge.bin')
    program = Program()
    program.load_bytes(machine)
    program.run()


class Logger:
    def __init__(self):
        self.state = "output"
        self.script = []
        self.last_register = {}
        self.last_memory = {}
        self.track = {
            2732, 2670, 2674, 2678, 2682, 2686, 
            2690, 2694, 2698, 2702, 2706, 2710, 
            2714, 2718, 2722, 2726, 2730, 
        }
        self.codes = set([
            'fbCcIPhFoGGd',
            'KtYzSlsHSBIz',
            'oNTFmoiTRTMG',
            'MBTdGgundHQG',
            'emBLbWMgDhds',
            'ipMlgrgDybOZ',
            'SlpnGuEnfhcE',
            'YOUlUoXioTpY',
        ])

    def add(self, value):
        self.script.append(value)

    def handle_memory(self, program):
        for i in range(len(program.registers)):
            if self.last_register.get(i, -1) != program.registers[i]:
                self.add(f"~r{i}{program.registers[i]}~")
                self.last_register[i] = program.registers[i]
        for cur in self.track:
            if cur < len(program.memory):
                if self.last_memory.get(cur, -1) != program.memory[cur]:
                    self.add(f"~v{cur}{program.memory[cur]}~")
                    self.last_memory[cur] = program.memory[cur]

    def add_message(self, state, value):
        if self.state != state:
            self.add(f"~m{state}~")
            self.state = state
        if value == "'":
            value = "\\'"
        elif value == "\n":
            value = "\\n"
        self.add(value)

    def handle_input(self, program, value):
        self.handle_memory(program)
        self.add_message("input", value)

    def handle_output(self, program, value):
        self.handle_memory(program)
        self.add_message("output", value)

    def finish(self):
        if self.script is not None:
            found = True
            while found:
                found = False
                digits = []
                for i in range(len(self.script)):
                    if self.script[i][0] != "~":
                        digits.append((self.script[i], i))
                    digits = digits[-12:]
                    if "".join([x[0] for x in digits]) in self.codes:
                        x = "".join([x[0] for x in digits])
                        found = True
                        print(x)
                        self.codes.remove(x)
                        a, b = digits[0][1], digits[-1][1] + 1
                        self.script = self.script[:a] + ["~mcode~"] + self.script[a:b] + ["~moutput~"] + self.script[b:]
                        break

            temp = ['']
            for cur in self.script:
                if len(temp[-1]) >= 100:
                    temp.append('')
                temp[-1] += cur

            with open("script.js", "w", newline='') as f:
                f.write("var script = '';\n")
                for cur in temp:
                    f.write(f"script += '{cur}'\n")
            self.script = None


@opt("Find all rooms")
def find_rooms():
    with zipfile.ZipFile(os.path.join("source", "challenge.zip"), 'r') as zip:
        machine = zip.read('challenge.bin')
    program = Program()
    program.load_bytes(machine)
    program.deserialize(os.path.join("source", "beach.zip"))
    program.run(abort_on_input=True, hide_output=True)

    known_rooms = set([
        2317, 2327, 2332, 2337, 2342, 2347, 2352, 2357, 2362, 
        2367, 2372, 2377, 2397, 2402, 2417, 2427, 2432, 2437, 
        2442, 2447, 2452, 2457, 2463, 2468, 2473, 2478, 2483, 
        2488, 2498, 2513, 2523, 2528, 2533, 2538, 2543, 2548, 
        2553, 2558, 2573, 2578, 2588, 2593, 2603, 2608, 2613, 
        2618, 2623, 2643, 
        2322, 2382, 2387, 2392, 2407, 2412, 2422, 2493, 2503, 
        2508, 2518, 2563, 2568, 2583, 2598, 2628, 2633, 2638, 
        2648, 2653, 2658, 
    ])

    start = program.clone()

    for i in range(2000, 3000):
        if i not in known_rooms:
            program = start.clone()
            program.memory[2732] = i
            program.input_buffer = "look\n"
            try:
                val = program.run(abort_on_input=True, hide_output=True)
                if val not in {"Unknown output character", "Halt instruction hit!"}:
                    print(i, val)
                    program.input_buffer = "look\n"
                    program.run(abort_on_input=True)
            except:
                pass


@opt("Run the program, with input")
def run_input(filename, log_all="no"):
    log_all = log_all.lower() in {"yes", "y", "true"}
    with zipfile.ZipFile(os.path.join("source", "challenge.zip"), 'r') as zip:
        machine = zip.read('challenge.bin')

    all_codes = _opcodes.copy()
    logger = Logger()
    if log_all:
        Program.set_logger(logger)
    program = Program()
    memory_log = {}

    with open(filename) as f:
        for cur in f:
            cur = cur.strip()
            if len(cur) == 0 or cur.startswith("##"):
                pass
            elif cur.startswith("#"):
                program.show(cur)
            elif cur.startswith("!"):
                program.show(cur, input=True)
                if cur.startswith("! log_memory "):
                    cur = cur[13:]
                    memory_log[int(cur)] = -1
                    program.show(f"> Memory log for {cur} enabled")
                elif cur.startswith("! log_reads"):
                    program.log_reads = True
                    program.show(f"> Read log enabled")
                elif cur.startswith("! reverse_mirror"):
                    for row in program.room[::-1]:
                        m = re.search("[ \"]([A-Za-z0-9]{12})[ \"]", row)
                        if m is not None:
                            break
                    code = m.group(1)[::-1]
                    reflect = {
                        "p": "q",
                        "q": "p",
                    }
                    code = "".join([reflect.get(x, x) for x in code])
                    program.show('> The code in the mirror is "' + code + '"')
                elif cur.startswith("! save"):
                    program.save_state.serialize("saved.zip")
                    program.show("> State saved to 'saved.zip'")
                elif cur.startswith("! opcodes "):
                    _opcodes.clear()
                    cur = [x for x in cur[10:].split(",")]
                    for op in all_codes:
                        if str(op) in cur or "all" in cur:
                            _opcodes[op] = all_codes[op]
                    _opcodes['names'] = all_codes['names']
                    program.show("> Enabled opcodes: " + ", ".join(cur))
                elif cur == "! run":
                    program = Program()
                    program.need_header = False
                    program.load_bytes(machine)
                    program.run(abort_on_input=True)
                elif cur == "! end":
                    program.show("> Goodbye!")
                    logger.finish()
                    exit(0)
                elif cur.startswith("! type "):
                    m = re.search("(.*):(.*),(.*)", cur[7:])
                    with open(os.path.join("source", m.group(1))) as f:
                        lines = f.readlines()
                        for i in range(int(m.group(2)) - 1, int(m.group(3))):
                            program.show("> " + lines[i].strip("\r\n"))
                elif cur.startswith("! decompile "):
                    cur = [int(x) for x in cur[12:].split(' ')]
                    pc = 0
                    program.show(f"> Decompiling from {cur[0]} to {cur[1]}:")
                    while pc < len(program.memory):
                        next_pc, info = program.decode(pc)
                        if pc >= cur[0]:
                            program.show("> " + info)
                        if next_pc > cur[1]:
                            break
                        pc = next_pc
                elif cur.startswith("! set_register "):
                    cur = cur[15:].split(' ')
                    program.registers[int(cur[0])-1] = int(cur[1])
                    program.show(f"> Register #{cur[0]} set to {cur[1]}")
                elif cur.startswith("! set_memory "):
                    cur = cur[13:].split(' ')
                    program.memory[int(cur[0])] = int(cur[1])
                    program.show(f"> Memory address {cur[0]} set to {cur[1]}")
                elif cur.startswith("! op "):
                    cur = cur[5:].split(' ')
                    program.memory[int(cur[0])] = _opcodes['names'][cur[1]]
                    program.show(f"> Set {cur[0]} to {cur[1]}")
                elif cur.startswith("! no_op "):
                    cur = int(cur[8:])
                    num_to_set = _opcodes[program.memory[cur]]['size']
                    for i in range(num_to_set):
                        program.memory[cur + i] = 21
                    program.show(f"> Set {num_to_set} values starting at {cur} to noop")
                else:
                    raise Exception()
            else:
                program.input_buffer = cur + "\n"
                program.run(abort_on_input=True)
                for x in memory_log:
                    if memory_log[x] != program.memory[x]:
                        val = program.memory[x]
                        program.show(f">> Memory {x} changed to {val}")
                        memory_log[x] = val

    logger.finish()
                

@opt("Run the program from a saved state")
def load(filename):
    with zipfile.ZipFile(os.path.join("source", "challenge.zip"), 'r') as zip:
        machine = zip.read('challenge.bin')
    program = Program()
    program.load_bytes(machine)
    program.deserialize(filename)
    program.run()


@opt("Solve the coin puzzle")
def solve_coins():
    coins = {
        "blue": 9,
        "concave": 7,
        "corroded": 3,
        "red": 2,
        "shiny": 5,
    }

    import itertools
    for order in itertools.permutations(coins):
        value = coins[order[0]] + coins[order[1]] * coins[order[2]] ** 2 + coins[order[3]] ** 3 - coins[order[4]]
        if value == 399:
            print("order = " + json.dumps(order))
            break


@opt("Find the target energy level")
def energy_level():
    def pow(base, exp, div):
        ret = 1
        for _ in range(exp):
            ret = (ret * base) % div
        return ret

    def f3(b, r8):
        d1 = pow(r8 + 1, b, 0x8000)
        d2 = pow(r8 + 1, b, r8 * 0x8000)
        d2 -= 1
        if d2 == -1:
            d2 = r8 - 1

        ret = d1 * ((r8 + 1) * (r8 + 1) + r8) + d2 // r8 * (2 * r8 + 1)
        return ret & 0x7fff

    def f41(r8):
        return f3(f3(r8, r8), r8)

    for i in range(1, 32879):
        result = f41(i)
        if i % 500 == 0:
            print(f"r8 = {i:5d}, f(4, 1) => {result}")
        if result == 6:
            print(f"The target is {i}")
            break


@opt("Find map of rooms")
def maps():
    with zipfile.ZipFile(os.path.join("source", "challenge.zip"), 'r') as zip:
        machine = zip.read('challenge.bin')

    todo = [2317]
    todo = [2488]
    todo = [2498]

    starts = [
        {'name': 'start', 'room': 2317, 'lantern': False},
        {'name': 'start_lantern', 'room': 2317, 'lantern': True},
        {'name': 'hq', 'room': 2488, 'lantern': False},
        {'name': 'island', 'room': 2498, 'lantern': False},
    ]

    for start in starts:
        rooms = {}
        todo = [start['room']]
        while len(todo) > 0:
            room = todo.pop(0)
            rooms[room] = {
                'id': room,
                'connections': [],
                'name': ''
            }
            program = Program()
            program.load_bytes(machine)
            program.deserialize(os.path.join("source", "start_state.zip"))
            program.memory[2732] = room
            if start['lantern']:
                program.memory[2682] = 0
            program.run(abort_on_input=True, hide_output=True)
            program.room = []
            program.input_buffer = "look\n"
            program.run(abort_on_input=True, hide_output=True)

            left = 0
            for cur in program.room:
                m = re.search("== (.*) ==", cur)
                if m is not None:
                    rooms[room]['name'] = m.group(1)
                m = re.search("There (are|is) ([0-9]+) exits{0,1}:", cur)
                if m is not None:
                    left = int(m.group(2))
                if left > 0 and cur.startswith("- "):
                    left -= 1
                    rooms[room]['connections'].append([cur[2:], -1])
            temp = program.clone()
            for i in range(len(rooms[room]['connections'])):
                program = temp.clone()
                program.input_buffer = rooms[room]['connections'][i][0] + "\n"
                program.run(abort_on_input=True, hide_output=True)
                rooms[room]['connections'][i][1] = program.memory[2732]
                if rooms[room]['connections'][i][1] not in rooms:
                    rooms[rooms[room]['connections'][i][1]] = None
                    todo.append(rooms[room]['connections'][i][1])

        import csv
        edge = 0
        with open("edges_" + start['name'] + ".csv", "w", newline='') as f_edges:
            cw_edges = csv.writer(f_edges)
            cw_edges.writerow(['id', 'source', 'source_name', 'dest', 'dest_name', 'dir'])

            for room in rooms.values():
                # cw_nodes.writerow(["node" + str(room['id']), room['name']])
                for dir, other in room['connections']:
                    edge += 1
                    cw_edges.writerow(["edge" + str(edge), "node" + str(room['id']), room['name'], "node" + str(other), rooms[other]['name'], dir])

        print("Done with " + start['name'])


@opt("Find layout of vault rooms")
def vaults():
    with zipfile.ZipFile(os.path.join("source", "challenge.zip"), 'r') as zip:
        machine = zip.read('challenge.bin')
    rooms = []
    ids = set()
    for cur in os.listdir("."):
        if cur.startswith("room_") and cur.endswith(".zip"):
            rooms.append({
                "id": int(cur[5:-4]),
                "name": cur,
                "connections": [],
                'oper': '',
                'special': '',
            })
            ids.add(int(cur[5:-4]))
    
    target = 0
    for room in rooms:
        program = Program()
        program.load_bytes(machine)
        program.deserialize(room['name'])
        program.run(abort_on_input=True, hide_output=True)
        program.room = []
        program.input_buffer = "look\n"
        program.run(abort_on_input=True, hide_output=True)
        steps = []
        for cur in program.room:
            m = re.search("The floor of this room is a large mosaic depicting a '(.*)' symbol.", cur)
            if m is not None:
                room['oper'] = m.group(1)
            m = re.search("The floor of this room is a large mosaic depicting the number '([0-9]+)'.", cur)
            if m is not None:
                room['oper'] = m.group(1)
            m = re.search("You notice the number '([0-9]+)' is carved", cur)
            if m is not None:
                room['oper'] = m.group(1)
            m = re.search("it has a large '([0-9]+)' carved into it", cur)
            if m is not None:
                target = int(m.group(1))
            if cur.startswith("- "):
                steps.append(cur[2:])
            if cur == "== Vault Antechamber ==":
                room['special'] = 'start'
            if cur == "== Vault Door ==":
                room['special'] = 'end'
        for step in steps:
            program.deserialize(room['name'])
            program.input_buffer = step + "\n"
            program.run(abort_on_input=True, hide_output=True)
            if program.memory[2732] in ids and program.memory[2732] != room['id']:
                room['connections'].append((step, program.memory[2732]))

    temp = rooms
    rooms = {}
    start, end = 0, 0
    for room in temp:
        rooms[room['id']] = room
        if room['special'] == 'start':
            start = room['id']
        if room['special'] == 'end':
            end = room['id']

    steps = deque([(start, [], [0, '+'])])
    while len(steps) > 0:
        room, path, val = steps.popleft()
        val.append(rooms[room]['oper'])
        if len(val) == 3:
            if val[1] == "+":
                val = [val[0] + int(val[2])]
            elif val[1] == "-":
                val = [val[0] - int(val[2])]
            elif val[1] == "*":
                val = [val[0] * int(val[2])]
            else:
                raise Exception(val)
        if room == end:
            if target == val[0]:
                for cur in path:
                    print(cur)
                steps = []
        else:
            for dir, sub in rooms[room]['connections']:
                if sub != start:
                    steps.append((sub, path[:] + [dir], val[:]))


@opt("Run the program, looking for events")
def auto(state=""):
    with zipfile.ZipFile(os.path.join("source", "challenge.zip"), 'r') as zip:
        machine = zip.read('challenge.bin')
    program = Program()
    program.load_bytes(machine)
    if len(state) == 0:
        state = os.path.join("source", "start_state.zip")
    program.deserialize(state)

    ignore = set([
        'The passage to the east looks very dark; you think you hear a Grue.',
        'The east passage appears very dark; you feel likely to be eaten by a Grue.',
        'emBLbWMgDhds',
        '\n\nThat door is locked.\n\nWhat do you do?',
        '\n\nYou have been eaten by a grue.',
        "\n\nThe vault door is sealed.\n\nWhat do you do?",
    ])

    states = [(program.clone(), None, [], [])]
    seen = set()
    while len(states) > 0:
        program, step, path, inv = states.pop(0)
        if step is not None:
            program.input_buffer += step + "\n"
            path = path + [step]

        program.run(abort_on_input=True, hide_output=True)
        room = "\n".join(program.room)

        m = re.search("Chiseled on the wall of one of the passageways, you see:\n\n    (?P<code>[a-zA-Z0-9]+)\n\nYou take note of this and keep walking.(?P<other>.*)", room, flags=re.DOTALL)
        if m is not None:
            if m.group("code") not in ignore:
                print(path)
                print("New code: " + m.group("code"))
                exit(1)
            else:
                room = m.group("other")

        room = re.sub("^\n\nAs you (approach the vault door|(enter|leave) the room).*?\n", "\n", room, flags=re.DOTALL)
        room = re.sub("^\n\nAs you (approach the vault door|(enter|leave) the room).*?\n", "\n", room, flags=re.DOTALL)

        if room not in ignore:
            m = re.search("^\n\n(?P<room>== .*? ==\n.*?)\n\n(?P<other>.*)\n\nWhat do you do\\?$", room, flags=re.DOTALL)
            if m is None:
                program.serialize("temp.zip")
                print("Room with odd description: " + json.dumps(room))
                exit(1)
            else:
                room, other = m.group("room"), m.group("other")
                mem = ""
                for key, value in program.changed.items():
                    if key < 3000:
                        mem += f"{key},{value}|"
                if mem not in seen:
                    seen.add(mem)
                    in_list = ""
                    lists = {
                        "door": [],
                        "item": [],
                        'other': [],
                    }

                    for cur in other.split("\n"):
                        if re.search("^There (are|is) [0-9]+ exits{0,1}:$", cur):
                            in_list = "door"
                        elif cur == "Things of interest here:":
                            in_list = "item"
                        elif cur == "":
                            in_list = ""
                        elif cur.startswith("- "):
                            lists[in_list].append(cur[2:])
                        elif re.search('[0-9_]+ \\+ [0-9_]+ \\* [0-9_]+\\^2 \\+ [0-9_]+\\^3 \\- [0-9_]+ = 399', cur):
                            lists["other"].append(cur)
                        else:
                            known = False
                            if cur in ignore:
                                known = True
                            if not known:
                                if re.search("The floor of this room is a large mosaic depicting a '(.*)' symbol.", cur):
                                    known = True
                            if not known:
                                if re.search("The floor of this room is a large mosaic depicting the number '([0-9]+)'.", cur):
                                    known = True
                            if not known:
                                print("Unknown line of desc: " + json.dumps(cur))
                                print("Inventory: ", inv)
                                exit(1)

                    for other in lists["other"]:
                        if len([x for x in inv if x.endswith("coin")]) == 5:
                            # From solve_coins
                            order = ["blue", "red", "shiny", "concave", "corroded"]
                            for test in order:
                                test += " coin"
                                inv.remove(test)
                                path = path + ['use ' + test]
                                program.input_buffer += path[-1] + "\n"
                                program.run(abort_on_input=True)
                            lists['door'] = ["look"] + lists['door']

                    for item in lists["item"]:
                        if item not in {"empty lantern", "can", "teleporter", 'business card', 'strange book', 'journal', 'orb'} and not item.endswith("coin"):
                            print(item)
                            print(inv)
                            print("-- Path --:")
                            for temp in path:
                                print(temp)
                            exit(1)
                        inv.append(item)
                        path = path + ['take ' + item]
                        program.input_buffer += path[-1] + "\n"
                        program.run(abort_on_input=True, hide_output=True)

                        if len(inv) == 2 and 'can' in inv and 'empty lantern' in inv:
                            path = path + ['use can']
                            program.input_buffer += path[-1] + "\n"
                            program.run(abort_on_input=True)
                            path = path + ['use lantern']
                            program.input_buffer += path[-1] + "\n"
                            program.run(abort_on_input=True)

                        if item == 'teleporter':
                            inv.remove('teleporter')
                            path = path + ['use teleporter']
                            program.input_buffer += path[-1] + "\n"
                            program.run(abort_on_input=True)

                            states = []
                            lists['door'] = ['look']
                    
                    if "== Vault" in room:
                        program.save_state.serialize("room_" + str(program.memory[2732]) + ".zip")
                    for door in lists["door"]:
                        states.append((program.clone(), door, path[:], inv[:]))

    print("--- All steps ---")
    for cur in path:
        print(cur)

    program.save_state.serialize(os.path.join('source', 'book.zip'))


if __name__ == "__main__":
    main_entry('func')
