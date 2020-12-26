#!/usr/bin/env python3

from command_opts import opt, main_entry

@opt("Hello, world")
def hello():
    print("This is a hello, world example")

if __name__ == "__main__":
    main_entry('func')
