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
import yaml
import tempfile
import xml.etree.ElementTree as ET
from nexus.lib.factory import SSHClient
from nexus.lib.ci_message import CI_MSG
from nexus.lib.factory import Platform
from nexus.lib import logger


class PkiTest(object):
    ''' Create environment to run pytest for Dogtag/Certificate Services '''

    def __init__(self, options=None, conf_dict=None):
        self.provisioner = options.provisioner
        self.conf_dict = conf_dict
        if self.provisioner == "beaker":
            self.username = self.conf_dict['beaker']['username']
            self.password = self.conf_dict['beaker']['password']
            nodes = self.conf_dict['jenkins']['existing_nodes']
        elif self.provisioner == "openstack":
            self.username = self.conf_dict['openstack']['username']
            self.password = self.conf_dict['openstack']['password']
            nodes = self.conf_dict['jenkins']['private_ips']
        else:
            logger.log.error("Unknown Provisioner")
        self.existing_nodes = [item.strip() for item in nodes.split(',')]
        if len(self.existing_nodes) is 1:
            nodes = conf_dict['jenkins']['private_ips']
            self.existing_nodes = [item.strip() for item in nodes.split(',')]
        self.workspace = self.conf_dict['jenkins']['workspace']
        self.jenkins_job_name = self.conf_dict['jenkins']['job_name']
        self.ssh_keys_priv = self.conf_dict['pytest']['ssh_keys_priv']
        self.ssh_keys_pub = conf_dict['pytest']['ssh_keys_pub']
        #self.tests_cfg = self.conf_dict['pytest']['tests_cfg']
        self.tests_to_run = self.conf_dict['pytest']['tests_to_run']
        self.tags_pattern = self.conf_dict['pytest']['tags_pattern']
        self.build_repo_tag = os.environ.get("BUILD_REPO_TAG")
        self.hosts = []
        self.etc_host = self.get_hosts()
        self.pytest_node = self.existing_nodes[0]

    def get_hosts(self):
        """ Get Hostnames of the provisioned vm's in openstack """
        etc_host_data = {}
        for host in self.existing_nodes:
            ssh_c = SSHClient(hostname = host, username = self.username, password = self.password)
            stdin, stdout, stderr = ssh_c.ExecuteCmd('hostname')
            for line in stdout.read().splitlines():
                logger.log.info(line)
                etc_host_data[host] = line
                self.hosts.append(line)
        return etc_host_data

    def copy_host_data(self):
        ''' copy the hosts data to all nodes '''
        (fd, path) = tempfile.mkstemp(prefix='tmphosts')
        for ip, hosts in self.etc_host.items():
            with open(path, 'a+') as fd:
                fd.write("%s %s\n"%(ip, hosts))

        target_hosts_file = '/tmp/update_etc_hosts'
        for host in self.existing_nodes:
            ssh_c = SSHClient(hostname=host, username=self.username,
                    password=self.password)
            ssh_c.CopyFiles(path, target_hosts_file)

        return target_hosts_file

    def update_etc_hosts(self):
        """ Update /etc/hosts with hostnames provisioned """
        target_hosts_file = self.copy_host_data()
        for host in self.existing_nodes:
            ssh_c = SSHClient(hostname=host, username=self.username,
                              password=self.password)
            stdout, stderr, exit_status = ssh_c.ExecuteScript("cat %s >> %s"%(target_hosts_file, '/etc/hosts'))
            if exit_status is 0:
                logger.log.info("%s host's /etc/hosts has been updated"%host)
            else:
                logger.log.info("%s host's /etc/hosts has not been updated"%host)
                return False
        return True

    def create_yaml(self):
        """ Create yaml for pytest multihost config file """
        if len(self.existing_nodes) is 2:
            mydata = {
                'test_dir': '/opt/rhqa_pki',
                'root_password': self.password,
                'domains': [
                    {
                        'name': 'testrelm.test',
                        'type': 'pki',
                        'hosts': [
                            {
                                'ip': self.existing_nodes[1],
                                'name': self.etc_host[self.existing_nodes[1]],
                                'external_hostname': self.etc_host[self.existing_nodes[1]],
                                'role':'master'
                            }
                        ]
                    }
                ]
            }

        elif len(self.existing_nodes) is 3:
            mydata = {
                'test_dir': '/opt/rhqa_pki',
                'root_password': self.password,
                'domains': [
                    {
                        'name': 'testrelm.test',
                        'type': 'pki',
                        'hosts': [
                            {
                                u'ip': self.existing_nodes[1],
                                u'name': self.etc_host[self.existing_nodes[1]],
                                u'external_hostname': self.etc_host[self.existing_nodes[1]],
                                u'role':'master'
                            },
                            {
                                'ip': self.existing_nodes[2],
                                'name': self.etc_host[self.existing_nodes[2]],
                                'external_hostname': self.etc_host[self.existing_nodes[2]],
                                'role':'replica'
                            }
                        ]
                    }
                ]
            }
        elif len(self.existing_nodes) is 4:
            mydata = {
                'test_dir': '/opt/rhqa_pki',
                'root_password': self.password,
                'domains': [
                    {
                        'name': 'testrelm.test',
                        'type': 'pki',
                        'hosts': [
                            {
                                'ip': self.existing_nodes[1],
                                'name': self.etc_host[self.existing_nodes[1]],
                                'external_hostname': self.etc_host[self.existing_nodes[1]],
                                'role':'master'
                            },
                            {
                                'ip': self.existing_nodes[2],
                                'name': self.etc_host[self.existing_nodes[2]],
                                'external_hostname': self.etc_host[self.existing_nodes[2]],
                                'role':'clone1'
                            },
                            {

                                'ip': self.existing_nodes[3],
                                'name': self.etc_host[self.existing_nodes[3]],
                                'external_hostname': self.etc_host[self.existing_nodes[3]],
                                'role':'clone2'
                            }
                        ]
                    }
                ]
            }
        with open('/tmp/mh_cfg', 'w') as yaml_file:
            yaml_file.write(yaml.dump(mydata, default_flow_style=False))
        return '/tmp/mh_cfg'

    def deploy_ssh_keys(self):
        """ Copy ssh keys to all existing nodes """
        source = self.ssh_keys_priv
        for host in self.existing_nodes:
            ssh_c = SSHClient(hostname=host, username=self.username,
                              password=self.password)
            stdout, stderr, exit_status = ssh_c.ExecuteScript("mkdir -p ~/.ssh/")
            if exit_status is 0:
                try:
                    source = self.conf_dict['pytest']['ssh_keys_priv']
                except KeyError as E:
                    logger.log.info("%s doesn't exist in conf file",E.message)
                else:
                    destination = '/root/.ssh/id_rsa'
                    logger.log.info("Copying %s to %s on %s" % (source, destination, host))
                    ssh_c.CopyFiles(source, destination)
                    stdout, stderr, exit_status = ssh_c.ExecuteScript("chmod 644 /root/.ssh/authorized_keys")
                    if exit_status is 0:
                        logger.log.info("Successfully set permission to authorized_keys")
                        stdout, stderr, exit_status = ssh_c.ExecuteScript("chmod 600 /root/.ssh/id_rsa")
                        if exit_status is 0:
                            logger.log.info("Successfull set permissions to /root/.ssh/id_rsa")
                            stdout, stderr, exit_status = ssh_c.ExecuteScript("chmod 700 /root/.ssh/")
                            if exit_status is 0:
                                logger.log.info("Successfully set permissions to /root/.ssh")
                                stdout, stderr, exit_status = ssh_c.ExecuteScript(
                                        'echo "StrictHostKeyChecking no" >> /root/.ssh/config')
                                if exit_status is 0:
                                    logger.log.info("ssh keys successfully deployed")
                                else:
                                    logger.log.info("ssh keys could not be successfully deployed")
                                    raise Exception
                            else:
                                logger.log.info("Unable to set permissions on /root/.ssh")
                                raise Exception
                        else:
                            logger.log.info("Unable to set permissions on /root/.ssh/id_rsa")
                            raise Exception
                    else:
                        logger.log.info("Unable to set permissions on authorized_keys")
                        raise Exception
                    return True
            else:
                return False

    def copy_extras_repo(self):
        """ Use yum-config-manager to create repo using a repo url """
        #connect to the first existing node
        ssh_c = SSHClient(
                hostname=self.pytest_node,
                username = self.username,
                password = self.password)
        try:
            myrepo = self.conf_dict['pytest']['extras_repo']
        except KeyError as E:
            logger.log.info("%s not found in nexus config"%(E.message))
            raise
        else:
            copy_extras_repo_cmd = "yum-config-manager --add-repo " + myrepo
            stdout, stderr, exit_status = ssh_c.ExecuteScript(copy_extras_repo_cmd)
            if exit_status is 0:
                logger.log.info("Successfully configure %s repo on %s"
                        %(myrepo, self.pytest_node))
                return True
            else:
                logger.log.info("Could not configure %s repo on %s"
                        %(myrepo, self.pytest_node))
                return False
    
    def install_prereqs(self):
        """ Install pre-requisites packages to run test suites """
        #connect to the host
        ssh_c = SSHClient(
                hostname=self.pytest_node,
                username = self.username,
                password = self.password)
        #fetch pytest_prereq parameter from nxus conf
        try:
            prereqs = self.conf_dict['pytest']['pytest_prereq']
        except KeyError as E:
            logger.log.info("There is no parameter %s in nexus conf"%(E.message))
            return False
        else:
            #install the packages on node 0
            pre_reqs = [item.strip() for item in prereqs.split(',')]
            pre_reqs_rpms = " ".join(pre_reqs)
            install_cmd = "yum install -y --nogpgcheck " + pre_reqs_rpms
            logger.log.info("Installing %s on %s"%(pre_reqs_rpms, self.pytest_node))
            stdout, stderr, exit_status = ssh_c.ExecuteScript(install_cmd)
            stdout.close()
            stderr.close()
            if exit_status is 0:
                logger.log.info("Successfully install %s on %s"%(pre_reqs_rpms, self.pytest_node))
                return True
            else:
                logger.log.info("Could not install %s on %s"%(pre_reqs_rpms, self.pytest_node))
                return False

    def pytest_setup(self):
        """ Setup pytest automation """
        #connect to host
        logger.log.info("Connecting to %s to setup pytest"%(self.pytest_node))
        ssh_c = SSHClient(
                hostname=self.pytest_node,
                username = self.username,
                password = self.password)
        #copy the multihost yaml file to pytest node
        try:
            git_repo_url = self.conf_dict['git']['git_repo_url']
        except KeyError as E:
            logger.log.info("No %s parameter found in nexus conf"%(E.message))
            return False
        else:
            get_tests = "git clone " + git_repo_url
            logger.log.info("git cloning %s on %s" % (git_repo_url, self.pytest_node))
            stdout, stderr, exit_status = ssh_c.ExecuteScript(get_tests)
            if exit_status is 0:
                stdout.close()
                stderr.close()
                logger.log.info("Installing pkilib on pytest node %s"%(self.pytest_node))
                try:
                    tests_base = self.conf_dict['pytest']['tests_base']
                except KeyError as Err:
                    logger.log.info("No %s found in nexus.conf"%(Err.message))
                    return False
                else:
                    stdout, stderr, exit_status = ssh_c.ExecuteScript("yum install -y pki-testlib")
                    if exit_status is 0:
                        logger.log.info("pki-testlib successfully installed")
                        return True
                    else:
                        return False

    def run_pytest(self, multihost_yaml_file):
        """ Run pytest command using the marker if provided """
        ssh_c = SSHClient(
                hostname=self.pytest_node,
                username = self.username,
                password = self.password)
        ssh_c.CopyFiles(multihost_yaml_file, multihost_yaml_file)
        try:
            tests_to_run = self.conf_dict['pytest']['tests_to_run']
        except KeyError as Err:
            logger.log.info("No parameter %s found in nexus configuration"%(Err.message))
            return False
        try:
            pytest_junit_loc = self.conf_dict['pytest']['pytest_junit_loc']
        except KeyError as Err:
            logger.log.info("No parameter %s found in nexus configuration"%(Err.message))
            return False

        ci_msg = CI_MSG()
        try:
            ttypes = ci_msg.get_ci_msg_value('testtypes')
        except Exception as Err:
            pass
            ttypes = None
        try:
            ttiers = ci_msg.get_ci_msg_value('testtiers')
        except Exception as Err:
            pass
            ttiers = None
        patterns = []

        if ttypes is None and ttiers is None:
            logger.log.info("Both test-tier and test-type options are none in CI_MESSAGE")
            pytest_cmd = "py.test -v --color=yes --junit-xml=%s --multihost-config=%s %s"%(
                    pytest_junit_loc, multihost_yaml_file, tests_to_run)
        else:
            pytest_cmd = "py.test -v --junit-xml=%s --multihost-config=%s %s"%(
                    pytest_junit_loc, multihost_yaml_file, tests_to_run)
        logger.log.info(pytest_cmd)

        if ttypes is None:
            logger.log.info("test-type is none in CI_MESSAGE")
        else:
            for item in ttypes:
                mystr = "-m" + " " + item
                patterns.append(mystr)

        if ttiers is None:
            logger.log.info("test-tier is none in CI_MESSAGE")
        else:
            for item in ttiers:
                mystr = "-m" + " " + item
                patterns.append(mystr)
        pytest_patterns = " ".join(patterns)
        pytest_cmd = pytest_cmd + " " + pytest_patterns
        logger.log.info(pytest_cmd)
        ssh_c = SSHClient(
                hostname=self.pytest_node,
                username = self.username,
                password = self.password)
        stdout,stderr,exit_status = ssh_c.ExecuteScript(pytest_cmd)
        if exit_status is 0:
           print("Script output: ", stdout.getvalue())
           stdout.close()
           stderr.close()
           return True
        else:
            print("Error: ", stderr.getvalue())
            stdout.close()
            stderr.close()
            return False
