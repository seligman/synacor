#!/usr/bin/env python3

from command_opts import opt, main_entry
from program import Program, _opcodes
import zipfile
import os
import re
import json


@opt("Run example program")
def test():
    program = Program()
    program.load_string("9,32768,32769,4,19,32768")
    program.run()


@opt("Run the program, showing memory changes")
def run_mem():
    with zipfile.ZipFile(os.path.join("source", "challenge.zip"), 'r') as zip:
        machine = zip.read('challenge.bin')
    program = Program()
    program.load_bytes(machine)
    memory = []
    while True:
        program.run(abort_on_input=True)
        if len(memory) == 0:
            memory = program.memory[:]
        else:
            for i in range(len(memory)):
                if memory[i] != program.memory[i]:
                    print(f"{i} => {memory[i]} != {program.memory[i]}")
        temp = input("Step? ")
        if temp == "reset":
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


@opt("Run the program, with input")
def run_input(filename):
    with zipfile.ZipFile(os.path.join("source", "challenge.zip"), 'r') as zip:
        machine = zip.read('challenge.bin')
    program = Program()
    program.load_bytes(machine)

    started = False

    with open(filename) as f:
        for cur in f:
            cur = cur.strip()
            if len(cur) == 0 or cur.startswith("##"):
                pass
            elif cur.startswith("#"):
                program.handle_io(cur)
            elif cur.startswith("!"):
                print("+> " + cur)
                program.handle_io("+> " + cur)
                if cur.startswith("! set_register "):
                    cur = cur[15:].split(' ')
                    program.registers[int(cur[0])-1] = int(cur[1])
                    msg = f"Ok, register #{cur[0]} set to {cur[1]}"
                    print(msg)
                    program.handle_io(msg)
                elif cur.startswith("! no_op "):
                    cur = int(cur[8:])
                    num_to_set = _opcodes[program.memory[cur]]['size']
                    for i in range(num_to_set):
                        program.memory[cur + i] = 21
                    msg = f"Ok, set {num_to_set} values starting at {cur} to noop"
                    print(msg)
                    program.handle_io(msg)
                    # program.log_all = True
                else:
                    raise Exception()
            else:
                if not started:
                    started = True
                    program.run(abort_on_input=True)
                program.input_buffer = cur + "\n"
                program.run(abort_on_input=True)
                

@opt("Solve the vault")
def vault():
    grid = [
        ["*", 8, "-", 1],
        [4, "*", 11, "*"],
        ["+", 4, "-", 18],
        [None, "-", 9, "*"],
    ]

    from collections import deque
    todo = deque([(0, 3, [], 22, None)])
    while len(todo) > 0:
        x, y, steps, val, op = todo.popleft()
        temp = grid[y][x]
        if isinstance(temp, int):
            if op == "+":
                val = val + temp
            elif op == "-":
                val = val - temp
            elif op == "*":
                val = val * temp
            op = None
        else:
            op = temp
        if (x, y) == (3, 0):
            if val == 30:
                print(steps, val)
                break
        else:
            for xo, yo, dir in [(0, -1, "n"), (0, 1, "s"), (-1, 0, "w"), (1, 0, "e")]:
                xt, yt = x + xo, y + yo
                if xt >= 0 and yt >= 0 and xt < 4 and yt < 4:
                    todo.append((xt, yt, steps[:] + [dir], val, op))


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
    # order = ['blue', 'red', 'shiny', 'concave', 'corroded']

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


@opt("Run the program, looking for events")
def auto():
    with zipfile.ZipFile(os.path.join("source", "challenge.zip"), 'r') as zip:
        machine = zip.read('challenge.bin')
    program = Program()
    program.load_bytes(machine)
    program.deserialize(os.path.join("source", "start_state.zip"))

    ignore = set([
        'The passage to the east looks very dark; you think you hear a Grue.',
        'The east passage appears very dark; you feel likely to be eaten by a Grue.',
        'emBLbWMgDhds',
        '\n\nThat door is locked.\n\nWhat do you do?',
        '\n\nYou have been eaten by a grue.',
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

        if room not in ignore:
            m = re.search("^\n\n(?P<room>== .*? ==\n.*?)\n\n(?P<other>.*)\n\nWhat do you do\\?$", room, flags=re.DOTALL)
            if m is None:
                program.serialize("temp.zip")
                print("Room with odd description: '" + room.replace("\n", "\\n") + "'")
                exit(1)
            else:
                room, other = m.group("room"), m.group("other")
                mem = ""
                for key, value in program.changed.items():
                    if key < 5000:
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
                            if cur not in ignore:
                                print("Unknown line of desc: '" + cur.replace("\n", "\\n") + "'")
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
                        if item not in {"empty lantern", "can", "teleporter", 'business card', 'strange book'} and not item.endswith("coin"):
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
                    
                    for door in lists["door"]:
                        states.append((program.clone(), door, path[:], inv[:]))

    print("--- All steps ---")
    for cur in path:
        print(cur)

    program.save_state.serialize(os.path.join('source', 'book.zip'))


if __name__ == "__main__":
    main_entry('func')
