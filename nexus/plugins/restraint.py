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
import xml.etree.ElementTree as ET
from nexus.lib.factory import SSHClient
from nexus.lib.factory import Threader
from nexus.lib.factory import Platform
from nexus.lib import logger

class Restraint():

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
        self.jenkins_job_name = conf_dict['jenkins']['job_name']
        self.build_repo_tag = os.environ.get("BUILD_REPO_TAG")
        self.git_repo_url = conf_dict['git']['git_repo_url']

    def restraint_setup(self, host, conf_dict):
        """
        wget appropriate restraint repo to respective nodes.
        Install restraint rpms and start its service.
        """

        subprocess.call(['yum', 'update', '-y', 'restraint-client'])
        logger.log.info("Updating restraint-client in local system")

        logger.log.info("Checking platform.dist of %s" % host)
        pltfrm = Platform(host, self.username, self.password)
        dist = pltfrm.GetDist()

        logger.log.info("Platform distribution for host %s is %s" % (host, dist))
        repo_out = "/etc/yum.repos.d/restraint.repo"

        ssh_c = SSHClient(hostname = host, username = \
                                  self.username, password = self.password)
        restraint_repo = conf_dict['restraint'][dist[1]]
        wget_cmd = "wget " + restraint_repo + " -O " + repo_out
        logger.log.info("%s to %s" % (host, wget_cmd))
        stdin, stdout, stderr = ssh_c.ExecuteCmd(wget_cmd)
        for line in stdout.read().splitlines(): logger.log.info(line)

        restraint_remove_rpms = conf_dict['restraint']['remove_rpm']
        remove_cmd = "yum remove -y " + restraint_remove_rpms
        logger.log.info("%s to %s" % (host, remove_cmd))
        stdin, stdout, stderr = ssh_c.ExecuteCmd(remove_cmd)
        for line in stdout.read().splitlines(): logger.log.info(line)

        """
        Check if OS is rhel5.11 and modify yum.conf to install
        architecture specific packages
        """
        if dist[1] == "5.11":
            yumconf = "/etc/yum.conf"
            yumconf_append = "echo 'multilib_policy = best' >> " + yumconf
            logger.log.info("%s is detected as 5.11. Setting multilib_policy \
                            best in /etc/yum.conf" % host)
            stdin, stdout, stderr = ssh_c.ExecuteCmd(yumconf_append)
            for line in stdout.read().splitlines(): logger.log.info(line)

        restraint_install_rpms = conf_dict['restraint']['install_rpm']
        install_cmd = "yum install -y " + restraint_install_rpms
        logger.log.info("%s to %s" % (host, install_cmd))
        stdin, stdout, stderr = ssh_c.ExecuteCmd(install_cmd)
        for line in stdout.read().splitlines(): logger.log.info(line)

        service = ("restraintd")
        start_service_cmd = ("service %s start; chkconfig %s on" % (service, \
                            service))
        logger.log.info("%s to %s" % (host, start_service_cmd))
        stdin, stdout, stderr = ssh_c.ExecuteCmd(start_service_cmd)
        for line in stdout.read().splitlines(): logger.log.info(line)

    def restraint_update_xml(self):
        """
        This function updates restraint xml with existing_resources with
        in place of hostname[int] string, also, it updates the git fetch
        URL and adds test branch name provided in conf file and if the
        value is default then use whatever is available in the restraint
        xml.
        """

        logger.log.info("Updating %s with existing_node information" % \
                        self.restraint_xml)
        node = 0
        host_num = 1
        host_recipe = []
        while node < len(self.existing_nodes):
            if os.path.exists(self.restraint_xml):
                host_num = str(host_num)
                hostname = ("hostname" + host_num);
                host_num = int(host_num)
                j = open(self.restraint_xml, 'r').read()
                m = j.replace(hostname, (self.existing_nodes[node]))
                f = open(self.restraint_xml, 'w')
                f.write(m)
                f.close()

                mystr = "-t" + " " + str(host_num) + '=' + self.existing_nodes[node]

                host_recipe.append(mystr)
                self.restraint_hosts = " ".join(host_recipe)
                node = node + 1
                host_num = host_num + 1
            else:
                logger.log.error("%s not found" % self.restraint_xml)
                sys.exit(2)

        if self.git_test_branch == "default":
            logger.log.info("Using the default branch to run tests.")
        else:
            self.git_test_branch_url = self.git_repo_url + "?" + self.git_test_branch
            self.git_test_branch_task = "/" + self.git_test_branch + "/"

            j = open(self.restraint_xml, 'r').read()
            m = j.replace(self.git_repo_url, self.git_test_branch_url)
            f = open(self.restraint_xml, 'w')
            f.write(m)
            f.close()

            j = open(self.restraint_xml, 'r').read()
            n = j.replace("/master/", self.git_test_branch_task)
            f = open(self.restraint_xml, 'w')
            f.write(n)
            f.close()
            logger.log.info("Updating restraint xml to use %s branch" % self.git_test_branch)

        logger.log.info("Updating restraint xml to use %s as task name" % self.job_name)
        j = open(self.restraint_xml, 'r').read()
        m = j.replace("JENKINS_JOB_NAME", self.job_name)
        f = open(self.restraint_xml, 'w')
        f.write(m)
        f.close()

        self.git_refspec = os.environ.get("GERRIT_REFSPEC")
        if self.git_refspec:
            logger.log.info("GERRIT_REFSPEC found in evnironment variable")
            tree = ET.parse(self.restraint_xml)
            root = tree.getroot()
            p = root.find("recipeSet")
            fetches = p.getiterator("fetch")
            for i in fetches:
                i.attrib["url"] = git_repo_url + "?" + self.git_refspec

            tree.write(self.restraint_xml)
            logger.log.info("Updated %s to fetch GERRIT_REFSPEC" % self.restraint_xml)

    def execute_restraint(self):
        """
        Check for the length of resources and build appropriate restraint
        command for both single and multi host execution.
        """

        subprocess.check_call(['cat', self.restraint_xml])
        if len(self.existing_nodes) == 1:
            host1 = ("1=%s:8081" % self.existing_nodes[0])
            try:
                subprocess.check_call(['restraint', '-j', \
                    self.restraint_xml, '-t', host1, '-v', '-v'])
                self.restraint_junit()
                self.restraint_html()
            except subprocess.CalledProcessError as e:
                self.restraint_junit()
                self.restraint_html()
                exit(e.returncode)
        else:
            rest_command = "restraint" + " " + "-j" + " " + self.restraint_xml \
                            + " " + self.restraint_hosts + " " + "-v" + " " + "-v"
            logger.log.info(rest_command)
            try:
                subprocess.check_call(rest_command.split(), shell=False)
                self.restraint_junit()
                self.restraint_html()
            except subprocess.CalledProcessError as e:
                self.restraint_junit()
                self.restraint_html()
                exit(e.returncode)

    def restraint_junit(self):
        """convert job.xml to junit.xml"""

        logger.log.info("Converting job.xml to junit")
        job2junit = "/usr/share/restraint/client/job2junit.xml"

        all_dirs = [d for d in os.listdir('.') if os.path.isdir(d)]
        latest_dir = max(all_dirs, key=os.path.getmtime)

        job_xml = os.path.join(latest_dir, "job.xml")

        if os.path.exists(job_xml):
            args = ('xsltproc', '/usr/share/restraint/client/job2junit.xml', job_xml)
            p_out = subprocess.PIPE
            p_err = subprocess.PIPE

            p = subprocess.Popen(args,stdout=p_out,stderr=p_err)
            stdout,stderr = p.communicate()

            fd = open("junit.xml", "w")
            fd.write(stdout)
            fd.close()
        else:
            logger.log.warn("job.xml not found.")

    def restraint_html(self):
        """get index.html from test directory to workspace"""

        logger.log.info("Get index.html from test directory to workspace")
        index_html = glob.glob("*/index.html")

        logger.log.info("index.html found at %s" % index_html)

        src = index_html[0]
        dst = "restraint_results.html"

        if os.path.exists(src):

            shutil.copyfile(src, dst)
        else:
            logger.log.warn("index.html not found.")


    def run_restraint(self, options, conf_dict):
        """
        Call restraint_setup function using threads per host.
        """

        logger.log.info("Running restraint...")
        threads = Threader()

        self.job_name = conf_dict['jenkins']['job_name']
        self.git_repo_url = conf_dict['git']['git_repo_url']
        self.git_test_branch = conf_dict['git']['git_test_branch']

        if options.restraint_xml is None:
            self.jenkins_workspace = conf_dict['jenkins']['workspace']
            try:
                self.restraint_xml_loc = conf_dict['restraint_jobs'][self.jenkins_job_name]
                self.restraint_xml = os.path.join(self.jenkins_workspace, \
                                     self.restraint_xml_loc)
            except KeyError:
                logger.log.warn("restraint xml not found in conf file, check with WHAT_TEST")
                self.what_test = os.environ.get("WHAT_TEST") + ".xml"
                self.restraint_job_xml_loc = conf_dict['restraint']['job_xml_loc']
                self.restraint_xml = os.path.join(self.restraint_job_xml_loc, self.what_test)

            threads.gather_results([threads.get_item(self.restraint_setup, \
                                    host, conf_dict) for host in \
                                    self.existing_nodes])
        else:
            self.restraint_xml = options.restraint_xml
            threads = Threader()
            threads.gather_results([threads.get_item(self.restraint_setup, \
                                    host, conf_dict) for host in \
                                    self.existing_nodes])

        logger.log.info("Using %s" % self.restraint_xml)

        if len(self.existing_nodes) == 1:
            logger.log.info("Found single host in existing_nodes")
            logger.log.info("single node: %s" % self.existing_nodes)
            self.restraint_update_xml()
            self.execute_restraint()
        else:
            logger.log.info("Found multiple hosts in existing_nodes")
            logger.log.info("multiple nodes: %s" % self.existing_nodes)
            self.restraint_update_xml()
            self.execute_restraint()
