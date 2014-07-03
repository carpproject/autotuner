from __future__ import print_function

import config
import sys

def verbose_message(string, module):
    if config.Arguments.verbose:
        print("[%s] %s" % (module, string), file=sys.stderr)
        
def warning_message(string):
    print("%s WARNING %s: %s" % ('*' * 10, string, '*' * 10), file=sys.stderr)

def summary_message(string, trailer=True):
    if trailer:
        print("=====> %s" % string)
    else:
        print(string)

def exit_message(string):
    print(string, file=sys.stderr)
    sys.exit(0)
