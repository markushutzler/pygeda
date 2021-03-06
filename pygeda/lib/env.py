#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pygeda - Support tool for Electonic Design Automation
# Copyright (C) 2017  Markus Hutzler
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function, absolute_import, division

import os
import subprocess
import re
import exceptions
import ConfigParser
from pygeda.lib.log import message


class Env(object):
    args = None
    schematic_files = None
    pcb_file = None
    project_package_path = None
    output_path = None
    project_name = None
    config = None
    package_path = []
    symbol_path = []
    _all_symbols = []
    _all_packages = []

    gEDA_path = None
    pcb_path = None

    def rc_properties(self, name, rcfile):
        if not os.path.isfile(rcfile):
            return []
        re_obj = re.compile(r"^\(%s (?P<value>.+?)\)$" % name)
        f = open(rcfile)
        ret = []
        for line in f.readlines():
            line = line.strip()
            x = re_obj.match(line)
            if x:
                ret.append(x.groups()[0])
        f.close()
        return ret

    def gschem_properties(self, name):
        ret = []
        ret += self.rc_properties(name, self.gEDA_path +
                                  '/share/gEDA/system-gschemrc')
        ret += self.rc_properties(name, './gafrc')
        return ret

    def gaf_properties(self, name):
        ret = []
        ret += self.rc_properties(name, self.gEDA_path +
                                  '/share/gEDA/system-gafrc')
        ret += self.rc_properties(name, './gafrc')
        return ret

    def get_bin_path(self, name):
        path = subprocess.check_output(["type", "-p", name]).strip()
        path = os.path.realpath(path)
        path = os.path.split(path)[0]
        path = os.path.split(path)[0]
        if not os.path.isdir(path):
            raise IOError

    def __init__(self):
        # getting system information (GSCHEM)
        try:
            gEDA_path = subprocess.check_output(["type",
                                                 "-p", 'gschem']).strip()
            gEDA_path = os.path.realpath(gEDA_path)
            gEDA_path = os.path.split(gEDA_path)[0]
            self.gEDA_path = os.path.split(gEDA_path)[0]
            if not os.path.isdir(self.gEDA_path):
                raise exceptions.IOError("'gschem' application not found.")
        except (exceptions.IOError, subprocess.CalledProcessError):
            raise exceptions.IOError("'gschem' application not found.")
        # getting system information (PCB)
        try:
            pcb_path = subprocess.check_output(["type", "-p", 'pcb']).strip()
            pcb_path = os.path.realpath(pcb_path)
            pcb_path = os.path.split(pcb_path)[0]
            self.pcb_path = os.path.split(pcb_path)[0]
            if not os.path.isdir(self.pcb_path):
                raise IOError("'pcb' application not found.")
        except (exceptions.IOError, subprocess.CalledProcessError):
            message("'pcb' application not found.", level="W")

        # collect symbol paths
        for path in self.gschem_properties('component-library'):
            self.symbol_path.append(path.strip('"'))
        self.symbol_path.append(self.gEDA_path+'/share/gEDA/sym')

        # collect packages
        self.package_path.append('./packages')
        if self.pcb_path:
            self.package_path.append(self.pcb_path+'/share/pcb/newlib')
            self.package_path.append(self.pcb_path+'/share/pcb/pcblib-newlib')

    @property
    def all_packages(self):
        if self._all_packages:
            return self._all_packages
        for path in self.package_path:
            for root, _, files in os.walk(path):
                for filename in files:
                    self._all_symbols.append(os.path.join(root, filename))
        return self._all_packages

    def package_files(self, filename):
        ret = []
        for pkg in self.all_packages:
            if os.path.basename(pkg) == filename:
                ret.append(pkg)
        return ret

    @property
    def all_symbols(self):
        if self._all_symbols:
            return self._all_symbols
        for path in self.symbol_path:
            for root, _, files in os.walk(path):
                for filename in files:
                    self._all_symbols.append(os.path.join(root, filename))
        return self._all_symbols

    def sym_files(self, filename):
        ret = []
        for sym in self.all_symbols:
            if os.path.basename(sym) == filename:
                ret.append(sym)
        return ret

    def get_config(self, section, field, default=None):
        try:
            return self.config.get(section, field)
        except ConfigParser.NoOptionError:
            return default
        except ConfigParser.NoSectionError:
            return default

    def check_project_file(self, file=None):
        """Check project file for all options needed."""
        if not file:
            return

        self.config = ConfigParser.ConfigParser()
        self.config.readfp(open(file))

        # check inventory
        self.inventory_server = self.get_config('Inventory', 'url')

        # checking files
        sch_files = self.get_config('Files', 'schematic', " ")
        self.schematic_files = sch_files.split(',')

        # checking other options
        self.pcb_file = self.get_config('Files', 'pcb')
        self.output_path = self.get_config('Files', 'output path')
        self.project_package_path = self.get_config('Files', 'package path')
        if self.project_package_path:
            self.package_path.append(self.project_package_path)

        # check section Options
        self.project_name = self.get_config('Options', 'project name')
        if self.project_name is None:
            message('No project name specified.', level="W")

        self.project_number = self.get_config('Options', 'project number')
        self.pcb_version = self.get_config('Options', 'pcb version')
