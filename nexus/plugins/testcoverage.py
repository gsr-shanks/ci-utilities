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
        self.coverage_dest = conf_dict['coverage']['coverage_dest']
        self.site_packages = conf_dict['coverage']['site_packages']
        self.site_customize = conf_dict['coverage']['site_customize']


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
        #FIXME join path self.site_packages + sitecustomize.py
        destination = "/usr/lib64/python2.7/site-packages/sitecustomize.py"
        logger.log.info("source file is %s" % source)
        ssh_c.CopyFiles(source, destination)

        source = self.coverage_conf
        destination = self.coverage_dest
        logger.log.info("source file is %s" % source)
        ssh_c.CopyFiles(source, destination)

    def coverage_reports(self, options, conf_dict):

        master = self.existing_nodes[0]
        ssh_c = SSHClient(hostname = master, username = \
                        self.username, password = self.password)

        coverage_html = "coverage html --rcfile=/root/.coveragerc"
        stdout,stderr,exit_status = ssh_c.ExecuteScript(coverage_html)
        output = stdout.getvalue()
        error = stderr.getvalue()

        if error:
            print "error running script: ", error
            print "Exit status: ", exit_status
        else:
            print "Script output: ", output

        coverage_cmd = "coverage report --rcfile=" + self.coverage_dest + ";" \
                        "coverage xml --rcfile=" + self.coverage_dest + ";" \
                        "coverage html --rcfile=" + self.coverage_dest
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
        coverage_data = conf_dict['coverage']['coverage_data']
        scp = SCPClient(ssh_c.get_transport())
        scp.get(coverage_data)

        coverage_xml = conf_dict['coverage']['coverage_xml']
        scp = SCPClient(ssh_c.get_transport())
        scp.get(coverage_xml)

        remotepath = conf_dict['coverage']['coverage_html']
        cmd = 'scp -r ' + master + ':' + remotepath + ' .'
        p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
        output = p.stdout.read()
        print output


    def run_coverage(self, options, conf_dict):

        self.update_coverage_conf(options, conf_dict)
        self.copy_site_custom(options, conf_dict)
