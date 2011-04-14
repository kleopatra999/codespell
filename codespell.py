#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.html.
"""
Copyright (C) 2010-2011  Lucas De Marchi <lucas.de.marchi@gmail.com>
Copyright (C) 2011  ProFUSION embedded systems
"""

import sys
import re
from optparse import OptionParser
import os

USAGE = """
\t%prog [OPTIONS] dict_filename [file1 file2 ... fileN]
"""
VERSION = '1.0'

misspellings = {}
options = None
encodings = [ 'utf-8', 'iso-8859-1' ]

#OPTIONS:
#
#ARGUMENTS:
#    dict_filename       The file containing the dictionary of misspellings.
#                        If set to '-', it will be read from stdin
#    file1 .. fileN      Files to check spelling

class Mispell:
    def __init__(self, data, fix, reason):
        self.data = data
        self.fix = fix
        self.reason = reason

class TermColors:
    def __init__(self):
        self.FILE = '\033[33m'
        self.WWORD = '\033[31m'
        self.FWORD = '\033[32m'
        self.DISABLE = '\033[0m'

    def disable(self):
        self.FILE = ''
        self.WWORD = ''
        self.FWORD = ''
        self.DISABLE = ''

# -.-:-.-:-.-:-.:-.-:-.-:-.-:-.-:-.:-.-:-.-:-.-:-.-:-.:-.-:-

def parse_options(args):
    parser = OptionParser(usage=USAGE, version=VERSION)

    parser.add_option('-d', '--disable-colors',
                        action = 'store_true', default = False,
                        help = 'Disable colors even when printing to terminal')
    parser.add_option('-r', '-R',
                        action = 'store_true', default = False,
                        dest = 'recursive',
                        help = 'parse directories recursively')
    parser.add_option('-w', '--write-changes',
                        action = 'store_true', default = False,
                        help = 'write changes in place if possible')

    (o, args) = parser.parse_args()
    if (len(args) < 1):
        print('ERROR: you need to specify a dictionary!', file=sys.stderr)
        parser.print_help()
        sys.exit(1)
    if (len(args) == 1):
        args.append('-')

    return o, args


def build_dict(filename):
    with open(filename, 'r') as f:
        for line in f:
            [key, data] = line.split('->')
            data = data.strip()
            fix = data.rfind(',')

            if fix < 0:
                fix = True
                reason = ''
            elif fix == (len(data) - 1):
                data = data[:fix]
                reason = ''
                fix = False
            else:
                reason = data[fix + 1:].strip()
                data = data[:fix]
                fix = False

            misspellings[key] = Mispell(data, fix, reason)

def ishidden(filename):
    bfilename = os.path.basename(filename)

    if bfilename != '' and bfilename != '.' and bfilename != '..' \
                                                 and bfilename[0] == '.':
        return True

    return False


def istextfile(filename):
    with open(filename, mode='rb') as f:
        s = f.read(1024)
        if 0 in s:
            return False

        return True

def parse_file(filename, colors):
    lines = None
    changed = False
    global misspellings
    global options
    global encodings

    if filename == '-':
        f = sys.stdin
        lines = f.readlines()
    else:
        # ignore binary files
        if not istextfile(filename):
            print("WARNING: Binary file: %s " % filename, file=sys.stderr)
            return

        curr = 0
        while True:
            try:
                f = open(filename, 'r', encoding=encodings[curr])
                lines = f.readlines()
                break
            except UnicodeDecodeError:
                print('WARNING: Decoding file %s' % filename, file=sys.stderr)
                print('WARNING: using encoding=%s failed. '
                                            % encodings[curr], file=sys.stderr)

                curr += 1
                print('WARNING: Trying next encoding: %s' % encodings[curr],
                                                            file=sys.stderr)

            finally:
                f.close()

        if not lines:
            print('ERROR: Could not detect encoding: %s' % filename,
                                                            file=sys.stderr)
            return

    i = 1
    for line in lines:
        for word in re.findall('\w+', line):
            lword = word.lower()
            if lword in misspellings:
                if word == word.capitalize():
                    fixword = misspellings[lword].data.capitalize()
                elif word == word.upper():
                    fixword = misspellings[lword].data.upper()
                else:
                    # even they are the same lower case or
                    # or we don't have any idea
                    fixword = misspellings[lword].data

                if options.write_changes and misspellings[lword].fix:
                    changed = True
                    lines[i - 1] = line.replace(word, fixword, 1)
                    continue

                cfilename = "%s%s%s" % (colors.FILE, filename, colors.DISABLE)
                cline = "%s%d%s" % (colors.FILE, i, colors.DISABLE)
                cwrongword = "%s%s%s" % (colors.WWORD, word, colors.DISABLE)
                crightword = "%s%s%s" % (colors.FWORD, fixword, colors.DISABLE)

                if misspellings[lword].reason:
                    creason = "  | %s%s%s" % (colors.FILE,
                                            misspellings[lword].reason,
                                            colors.DISABLE)
                else:
                    creason = ''

                if filename != '-':
                    print("%(FILENAME)s:%(LINE)s: %(WRONGWORD)s "       \
                            " ==> %(RIGHTWORD)s%(REASON)s"
                            % {'FILENAME': cfilename, 'LINE': cline,
                               'WRONGWORD': cwrongword,
                               'RIGHTWORD': crightword, 'REASON': creason })
                else:
                    print('%(LINE)s: %(STRLINE)s\n\t%(WRONGWORD)s ' \
                            '==> %(RIGHTWORD)s%(REASON)s'
                            % { 'LINE': cline, 'STRLINE': line.strip(),
                                'WRONGWORD': cwrongword,
                               'RIGHTWORD': crightword, 'REASON': creason })
        i += 1

    if changed:
        if filename == '-':
            print("---")
            for line in lines:
                print(line, end='')
        else:
            print("%sFIXED:%s %s" % (colors.FWORD, colors.DISABLE, filename),
                                    file=sys.stderr)
            f = open(filename, 'w')
            f.writelines(lines)
            f.close()


def main(*args):
    global options
    (options, args) = parse_options(args)

    build_dict(args[0])
    colors = TermColors();
    if options.disable_colors:
        colors.disable()

    for filename in args[1:]:
        # ignore hidden files
        if ishidden(filename):
            continue

        if not options.recursive and os.path.isdir(filename):
            continue

        if os.path.isdir(filename):
            for root, dirs, files in os.walk(filename):
                i = 0
                for d in dirs:
                    if ishidden(d):
                        del dirs[i]
                    else:
                        i += 1

                for file in files:
                    if os.path.islink(file):
                        continue

                    parse_file(os.path.join(root, file), colors)

            continue

        parse_file(filename, colors)

if __name__ == '__main__':
    sys.exit(main(*sys.argv))
