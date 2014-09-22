#!/usr/bin/python
# Copyright (c) 2014 Red Hat, Inc. All rights reserved.
#
# This copyrighted material is made available to anyone wishing
# to use, modify, copy, or redistribute it subject to the terms
# and conditions of the GNU General Public License version 2.
#
# You should have received a copy of the GNU General Public
# License along with this program; if not, write to the Free
# Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
# Boston, MA 02110-1301, USA.

import sys
import os
import paramiko
import util


username = "root"
password = "whatever"

class ExistingNodes():

    def env_check(self):
        util.log.info("Checking if EXISTING_NODES variable is empty")
        host_in = os.environ.get('EXISTING_NODES')
        if not host_in:
            util.log.error("List is empty!")
            sys.exit(1)
        else:
            util.log.info("EXISTING_NODES list is not empty ... ready to go!")

    def node_check(self):
        my_nodes = tuple(os.environ.get('EXISTING_NODES').split(","))
        if len(my_nodes) == 1:
            util.log.info("I have only %s and it is my MASTER." % my_nodes[0])
            return my_nodes
        else:
            util.log.info("I have multiple resources")
            return my_nodes


class SetupRestraint():

    def restraint_repo(self):
        resources = ExistingNodes()
        my_nodes = resources.node_check()

        repo_url = "http://file.bos.redhat.com/~bpeck/restraint/el6.repo"
        get_repo = ("wget %s -O /etc/yum.repos.d/restraint.repo" % repo_url)

        for node in my_nodes:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(my_nodes[0], username=username,
                        password=password)
            util.log.info("Executing command %s" % get_repo)
            stdin, stdout, stderr = ssh.exec_command(get_repo)
            for line in stdout.read().splitlines():
                util.log.info('host: %s: %s' % (my_nodes[0], line))

    def restraint_install(self):
        resources = ExistingNodes()
        my_nodes = resources.node_check()

        pkgs = ("restraint staf")
        yum_install = ("yum install -y %s" % pkgs)

        for node in my_nodes:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(my_nodes[0], username=username,
                        password=password)
            util.log.info("Executing command %s" % yum_install)
            stdin, stdout, stderr = ssh.exec_command(yum_install)
            for line in stdout.read().splitlines():
                if "error" in line:
                    util.log.error('host: %s: %s' % (my_node[0], line))
                    sys.exit(1)
                else:
                    util.log.info('host: %s: %s' % (my_nodes[0], line))

    def restraint_start(self):
        resources = ExistingNodes()
        my_nodes = resources.node_check()

        service = ("restraintd")
        start_service = ("service %s start; chkconfig %s on" % (service, service))

        for node in my_nodes:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(my_nodes[0], username=username,
                        password=password)
            util.log.info("Executing command %s" % start_service)
            stdin, stdout, stderr = ssh.exec_command(start_service)
            for line in stdout.read().splitlines():
                if "error" in line:
                    util.log.error('host: %s: %s' % (my_node[0], line))
                    sys.exit(1)
                else:
                    util.log.info('host: %s: %s' % (my_nodes[0], line))

