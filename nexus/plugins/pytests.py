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
import glob
import subprocess
import shutil
from scp import SCPClient
from nexus.lib.factory import SSHClient
from nexus.lib.factory import Threader
from nexus.lib import logger

class Pytest():

    def __init__(self, options, conf_dict):

        self.provisioner = options.provisioner

        nodes = conf_dict['jenkins']['existing_nodes']
        self.existing_nodes = [item.strip() for item in nodes.split(',')]

        if self.provisioner == "beaker":
            self.username = conf_dict['beaker']['username']
            self.password = conf_dict['beaker']['password']
        elif self.provisioner == "openstack":
            self.username = conf_dict['openstack']['username']
            self.password = conf_dict['openstack']['password']
        else:
            logger.log.error("Unknown provisioner")

        self.workspace = conf_dict['jenkins']['workspace']
        self.jenkins_job_name = conf_dict['jenkins']['job_name']
        self.ssh_keys_priv = conf_dict['pytest']['ssh_keys_priv']
        self.ssh_keys_pub = conf_dict['pytest']['ssh_keys_pub']
        self.tests_cfg = conf_dict['pytest']['tests_cfg']
        self.tests_to_run = conf_dict['pytest']['tests_to_run']
        self.tags_pattern = conf_dict['pytest']['tags_pattern']
        self.build_repo_tag = os.environ.get("BUILD_REPO_TAG")

    def deploy_ssh_keys(self, host, conf_dict):
        ssh_c = SSHClient(hostname = host, username = \
                        self.username, password = self.password)

        stdin, stdout, stderr = ssh_c.ExecuteCmd('mkdir -p ~/.ssh/')
        for line in stdout.read().splitlines(): logger.log.info(line)

        source = self.ssh_keys_priv
        destination = "/root/.ssh/id_rsa"
        logger.log.info("Copying %s to %s on %s" % (source, destination, host))
        ssh_c.CopyFiles(source, destination)

        source = self.ssh_keys_pub
        destination = "/root/.ssh/authorized_keys"
        logger.log.info("Copying %s to %s on %s" % (source, destination, host))
        ssh_c.CopyFiles(source, destination)

        stdin, stdout, stderr = ssh_c.ExecuteCmd('chmod 644 /root/.ssh/authorized_keys')
        for line in stdout.read().splitlines(): logger.log.info(line)

        stdin, stdout, stderr = ssh_c.ExecuteCmd('chmod 600 /root/.ssh/id_rsa')
        for line in stdout.read().splitlines(): logger.log.info(line)

        stdin, stdout, stderr = ssh_c.ExecuteCmd('chmod 700 /root/.ssh/')
        for line in stdout.read().splitlines(): logger.log.info(line)

        stdin, stdout, stderr = ssh_c.ExecuteCmd('echo "StrictHostKeyChecking no" >> /root/.ssh/config')
        for line in stdout.read().splitlines(): logger.log.info(line)


    def copy_extras_repo(self, host, conf_dict):
        ssh_c = SSHClient(hostname = host, username = \
                        self.username, password = self.password)

        self.extras_repo = conf_dict['pytest']['extras_repo']

        logger.log.info("Adding extras repo to %s", host)
        copy_extras_repo_cmd = "yum-config-manager --add-repo " + self.extras_repo

        stdin, stdout, stderr = ssh_c.ExecuteCmd(copy_extras_repo_cmd)
        for line in stdout.read().splitlines(): logger.log.info(line)

    def install_prereqs(self, host, conf_dict):
        ssh_c = SSHClient(hostname = host, username = \
                        self.username, password = self.password)

        prereqs = conf_dict['pytest']['pytest_prereq']
        self.prereqs = [item.strip() for item in prereqs.split(',')]
        self.prereqs_rpms = " ".join(self.prereqs)
        install_cmd = "yum install -y --nogpgcheck " + self.prereqs_rpms
        logger.log.info("Installing %s on %s" % (self.prereqs_rpms, host))
        stdin, stdout, stderr = ssh_c.ExecuteCmd(install_cmd)
        for line in stdout.read().splitlines(): logger.log.info(line)

    def pytest_setup(self, host, conf_dict):
        ssh_c = SSHClient(hostname = host, username = \
                        self.username, password = self.password)

        self.tests_cfg = conf_dict['pytest']['tests_cfg']

        git_clone = "git clone "
        self.git_repo_url = conf_dict['git']['git_repo_url']
        get_tests = git_clone + self.git_repo_url

        logger.log.info("git cloning %s on %s" % (self.git_repo_url, host))
        stdin, stdout, stderr = ssh_c.ExecuteCmd(get_tests)
        for line in stdout.read().splitlines(): logger.log.info(line)

        #TODO mkdir and touch commands should be handled in automation
        stdin, stdout, stderr = ssh_c.ExecuteCmd('mkdir -p /root/multihost_tests')
        for line in stdout.read().splitlines(): logger.log.info(line)

        stdin, stdout, stderr = ssh_c.ExecuteCmd('touch /root/multihost_tests/env.sh')
        for line in stdout.read().splitlines(): logger.log.info(line)


        source = self.tests_cfg
        destination = self.tests_cfg

        logger.log.info("source file is %s" % source)
        logger.log.info("destination file is %s on %s" % (destination, host))

        ssh_c.CopyFiles(source, destination)

        self.tests_base = conf_dict['pytest']['tests_base']
        stdin, stdout, stderr = ssh_c.ExecuteCmd('cd' + self.tests_base  + '; python setup.py install')
        for line in stdout.read().splitlines(): logger.log.info(line)

    def copy_testout_junit(self, options, conf_dict):
        master = self.existing_nodes[0]
        ssh_c = SSHClient(hostname = master, username = \
                        self.username, password = self.password)
        remote_file = conf_dict['pytest']['pytest_junit_loc']

        scp = SCPClient(ssh_c.get_transport())
        scp.get(remote_file)

    def run_pytest(self, options, conf_dict):

        threads = Threader()

        threads.gather_results([threads.get_item(self.deploy_ssh_keys, \
                                host, conf_dict) for host in \
                                self.existing_nodes])

        threads.gather_results([threads.get_item(self.install_prereqs, \
                                host, conf_dict) for host in \
                                self.existing_nodes])

        threads.gather_results([threads.get_item(self.copy_extras_repo, \
                                host, conf_dict) for host in \
                                self.existing_nodes])

        threads.gather_results([threads.get_item(self.install_prereqs, \
                                host, conf_dict) for host in \
                                self.existing_nodes])

        logger.log.info("Updating %s with existing_nodes information" % self.tests_cfg)

        node = 0
        host_num = 1
        host_recipe = []
        while node < len(self.existing_nodes):
            host_num = str(host_num)
            hostname = ("hostname" + host_num);
            host_num = int(host_num)
            j = open(self.tests_cfg, 'r').read()
            m = j.replace(hostname, (self.existing_nodes[node]))
            f = open(self.tests_cfg, 'w')
            f.write(m)
            f.close()

            node = node + 1
            host_num = host_num + 1

        threads.gather_results([threads.get_item(self.pytest_setup, \
                                host, conf_dict) for host in \
                                self.existing_nodes])

        self.tests_to_run = conf_dict['pytest']['tests_to_run']
        self.tests_cfg = conf_dict['pytest']['tests_cfg']
        self.pytest_junit_loc = conf_dict['pytest']['pytest_junit_loc']

        pytest_cmd = "py.test --junit-xml=" + self.pytest_junit_loc + \
            " --multihost-config=" + self.tests_cfg + " " + self.tests_to_run

        host = self.existing_nodes[0]

        ssh_c = SSHClient(hostname = host, username = \
                        self.username, password = self.password)
        stdout,stderr,exit_status = ssh_c.ExecuteScript(pytest_cmd)
        output = stdout.getvalue()
        error = stderr.getvalue()

        if error:
            print "error running script: ", error
            print "Exit status : ", exit_status
        else:
            print "Script Output: ", output

        stdout.close()
        stderr.close()

        self.copy_testout_junit(options, conf_dict)
