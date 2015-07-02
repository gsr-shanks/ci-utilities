#!/usr/bin/python
# Copyright (c) 2015 Red Hat, Inc. All rights reserved.
#
# This copyrighted material is made available to anyone wishing
# to use, modify, copy, or redistribute it subject to the terms
# and conditions of the GNU General Public License version 2.
#
# You should have received a copy of the GNU General Public
# License along with this program; if not, write to the Free
# Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
# Boston, MA 02110-1301, USA.

import os
import sys
import platform
from subprocess import Popen, PIPE, STDOUT
from scp import SCPClient
from nexus.lib.factory import SSHClient
from nexus.lib.factory import Threader
from nexus.lib import logger
from nexus.lib.ci_message import CI_MSG


class Testcoverage():

    def __init__(self, options, conf_dict):

        self.provisioner = options.provisioner

        if self.provisioner == "beaker":
            self.username = conf_dict['beaker']['username']
            self.password = conf_dict['beaker']['password']
            nodes = conf_dict['jenkins']['existing_nodes']
        elif self.provisioner == "openstack":
            self.username = conf_dict['openstack']['username']
            self.password = conf_dict['openstack']['password']
            nodes = conf_dict['jenkins']['private_ips']
        else:
            logger.log.error("Unknown provisioner")

        self.existing_nodes = [item.strip() for item in nodes.split(',')]
        self.coverage_conf = conf_dict['coverage']['coverage_conf']
        self.site_packages = conf_dict['coverage']['site_packages']
        self.site_customize = conf_dict['coverage']['site_customize']
        self.coverage_rc = conf_dict['coverage']['coverage_rc']


    def update_coverage_conf(self, options, conf_dict):

        j = open(self.coverage_conf, 'r').read()
        m = j.replace("SITEPACKAGES", self.site_packages)
        f = open(self.coverage_conf, 'w')
        f.write(m)
        f.close()

        master = self.existing_nodes[0]
        ssh_c = SSHClient(hostname = master, username = \
                        self.username, password = self.password)

    def copy_site_custom(self, options, conf_dict):

        master = self.existing_nodes[0]
        ssh_c = SSHClient(hostname = master, username = \
                        self.username, password = self.password)

        source = self.site_customize
        destination = os.path.join(self.site_packages, 'sitecustomize.py')
        logger.log.info("source file is %s" % source)
        ssh_c.CopyFiles(source, destination)

        source = self.coverage_conf
        destination = self.coverage_rc
        logger.log.info("source file is %s" % source)
        ssh_c.CopyFiles(source, destination)

    def coverage_reports(self, options, conf_dict):

        master = self.existing_nodes[0]
        ssh_c = SSHClient(hostname = master, username = \
                        self.username, password = self.password)

        coverage_combine = "coverage combine --rcfile=" + self.coverage_rc
        stdout,stderr,exit_status = ssh_c.ExecuteScript(coverage_combine)
        output = stdout.getvalue()
        error = stderr.getvalue()

        if error:
            print "error running script: ", error
            print "Exit status: ", exit_status
        else:
            print "Script output: ", output

        coverage_cmd = "coverage report --rcfile=" + self.coverage_rc + ";" \
                        "coverage xml --rcfile=" + self.coverage_rc + ";" \
                        "coverage html --rcfile=" + self.coverage_rc
        stdout,stderr,exit_status = ssh_c.ExecuteScript(coverage_cmd)
        output = stdout.getvalue()
        error = stderr.getvalue()

        if error:
            print "error running script: ", error
            print "Exit status: ", exit_status
        else:
            print "Script output: ", output


    def get_reports(self, options, conf_dict):

        master = self.existing_nodes[0]
        ssh_c = SSHClient(hostname = master, username = \
                        self.username, password = self.password)

        coverage_xml = conf_dict['coverage']['coverage_xml']
        scp = SCPClient(ssh_c.get_transport())
        scp.get(coverage_xml)


    def run_coverage(self, options, conf_dict):

        self.update_coverage_conf(options, conf_dict)
        self.copy_site_custom(options, conf_dict)
