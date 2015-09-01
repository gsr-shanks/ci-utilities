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
from nexus.lib.factory import SSHClient
from nexus.lib.factory import Threader
from nexus.lib.factory import Platform
from nexus.lib import logger

class Repos():

    def __init__(self, options, conf_dict):

        if options.provisioner == 'beaker':
            self.username = conf_dict['beaker']['username']
            self.password = conf_dict['beaker']['password']
        elif options.provisioner == 'openstack':
            self.username = conf_dict['openstack']['username']
            self.password = conf_dict['openstack']['password']

        self.framework = options.framework
        nodes = conf_dict['jenkins']['existing_nodes']
        self.existing_nodes = [item.strip() for item in nodes.split(',')]
        self.repos_section = 'repos'

        self.jenkins_job_name = conf_dict['jenkins']['job_name']
        self.brew_tag = conf_dict['brew']['brew_tag']
        self.brew_arch = conf_dict['brew']['brew_arch']
        self.build_repo_tag = os.environ.get("BUILD_REPO_TAG")
        self.static_repo_url = os.environ.get("STATIC_REPO_URLS")
        self.task_repo_urls = os.environ.get("TASK_REPO_URLS")

        if self.task_repo_urls:
            self.task_repo_urls = self.task_repo_urls.split(';')
        else:
            logger.log.info("Task repo urls not found.")

    def my_build_repo(self, host, conf_dict):

        source = self.build_repo
        destination = "/etc/yum.repos.d/my_build.repo"

        logger.log.info("Copying %s to %s on %s" % (source, destination, host))
        ssh_c = SSHClient(hostname = host, username = \
                self.username, password = self.password)
        ssh_c.CopyFiles(source, destination)

    def copy_build_repo(self, host, conf_dict):
        """copy the brew build repo to all the existing nodes"""

        self.build_repo_file = self.build_repo_tag + ".repo"
        self.build_repo_url = os.environ.get("BUILD_REPO_URL")

        logger.log.info("Copying %s to %s" % (self.build_repo_file, host))
        repo = open(self.build_repo_file, "w")
        repo.write( "[" + self.build_repo_tag + "]\n");
        repo.write( "name=" + self.build_repo_tag + "\n" );
        repo.write( "baseurl=" + self.build_repo_url + "\n" );
        repo.write( "enabled=1\n") ;
        repo.write( "gpgcheck=0\n" );
        repo.write( "skip_if_unavailable=1\n" );
        repo.close()

        source = self.build_repo_file
        destination = "/etc/yum.repos.d/" + source

        pltfrm = Platform(host, self.username, self.password)
        dist = pltfrm.GetDist()
        distver = str(dist[1]).replace('.','')
        if distver in self.build_repo_file:
            logger.log.info("source file is %s" % source)
            logger.log.info("destination file is %s" % destination)

            ssh_c = SSHClient(hostname = host, username = \
                                      self.username, password = self.password)
            ssh_c.CopyFiles(source, destination)
        else:
            logger.log.info("Destination %s is %s" % (host, dist))
            logger.log.info("Not adding repo file to %s" % host)

    def copy_async_updates_repo(self, host, conf_dict):
        """copy the async updates repo to all the existing nodes"""

        try:
            logger.log.info("Checking platform.dist of %s to get the right batched repo" % host)
            pltfrm = Platform(host, self.username, self.password)
            dist = pltfrm.GetDist()

            logger.log.info("Platform distribution for host %s is %s" % (host, dist))
            self.async_updates_url = conf_dict['async_repos'][dist[1]]

            self.build_repo_file = "async_updates_" + host + ".repo"

            logger.log.info("Creating async updates build repo file %s" % self.build_repo_file)
            repo = open(self.build_repo_file, "w")
            repo.write( "[" + "async_updates" + "]\n");
            repo.write( "name=" + "async_updates" + "\n" );
            repo.write( "baseurl=" + self.async_updates_url + "\n" );
            repo.write( "enabled=1\n") ;
            repo.write( "gpgcheck=0\n" );
            repo.write( "skip_if_unavailable=1\n" );
            repo.close()

            source = self.build_repo_file
            destination = "/etc/yum.repos.d/" + source

            logger.log.info("source file is %s" % source)
            logger.log.info("destination file is %s" % destination)

            ssh_c = SSHClient(hostname = host, username = \
                                      self.username, password = self.password)
            ssh_c.CopyFiles(source, destination)
        except KeyError, e:
            logger.log.error("%s key for async_updates_url does not exists in conf." % e)


    def copy_task_repo(self, host, conf_dict):
        """
        Create TASK_REPO_URLS repo conf
        """

        if self.task_repo_urls:

            self.task_repo_urls = os.environ.get("TASK_REPO_URLS")
            self.task_repo_urls = self.task_repo_urls.split(';')

            logger.log.info("Checking platform.dist of %s" % host)

            pltfrm = Platform(host, self.username, self.password)
            dist = pltfrm.GetDist()

            logger.log.info("Platform arch for host %s is %s" % (host, self.brew_arch))
            logger.log.info("Platform distribution for host %s is %s" % (host, dist))
            logger.log.info(self.task_repo_urls)

            if len(self.task_repo_urls) == 1:
                r = self.task_repo_urls
            else:
                r = [s for s in self.task_repo_urls if self.brew_arch in s]

            logger.log.info("Adding task_repo %s to %s" % (r[0], host))
            copy_task_repo_cmd = "yum-config-manager --add-repo " + r[0]
            ssh_c = SSHClient(hostname = host, username = \
                                  self.username, password = self.password)

            stdin, stdout, stderr = ssh_c.ExecuteCmd(copy_task_repo_cmd)
            for line in stdout.read().splitlines(): logger.log.info(line)
        else:
            logger.log.info("TASK_REPO_URLS env variable not found")


    def copy_static_repo(self, host, conf_dict):
        """
        Create STATIC_REPO_URLS repo conf
        """

        logger.log.info("Checking platform.dist of %s" % host)
        pltfrm = Platform(host, self.username, self.password)
        dist = pltfrm.GetDist()

        logger.log.info("Platform distribution for host %s is %s" % (host, dist))

        if dist[1] in self.static_repo_url:
            self.static_repo_url_arch = self.static_repo_url + "/" + self.brew_arch
            logger.log.info("Adding static_repo %s to %s" % (self.static_repo_url_arch, host))
            copy_static_repo_cmd = "yum-config-manager --add-repo " + self.static_repo_url_arch
            ssh_c = SSHClient(hostname = host, username = \
                                      self.username, password = self.password)

            stdin, stdout, stderr = ssh_c.ExecuteCmd(copy_static_repo_cmd)
            for line in stdout.read().splitlines(): logger.log.info(line)
        else:
            logger.log.info("%s is not for %s dist" % (self.static_repo_url, dist))


    def create_repos_section(self, host, conf_dict):
        """
        Blindly use yum-config-manager to create repos for
        urls provided in repos section
        """

        ssh_c = SSHClient(hostname = host, username = \
                self.username, password = self.password)

        repo_section_name = conf_dict[self.repos_section]
        for key, value in repo_section_name.iteritems():

            logger.log.info("Adding repo %s to %s" % (value, host))
            copy_static_repo_cmd = "yum-config-manager --add-repo " + value

            stdin, stdout, stderr = ssh_c.ExecuteCmd(copy_static_repo_cmd)


    def install_yum_utils(self, host, conf_dict):
        """
        yum-utils should be installed for yum-config-manager command to be made
        available on all the hosts to configure yum repos and disable gpgcheck.
        """

        ssh_c = SSHClient(hostname = host, username = \
                self.username, password = self.password)

        logger.log.info("Installing yum-utils on %s" % host)

        if options.provisioner == 'openstack' and self.framework == 'restraint':
            install_yum_utils_cmd = "yum install -y --nogpgcheck yum-utils wget beakerlib"
        else:
            install_yum_utils_cmd = "yum install -y --nogpgcheck yum-utils"

        stdin, stdout, stderr = ssh_c.ExecuteCmd(install_yum_utils_cmd)

        logger.log.info("Disabling gpgcheck in /etc/yum.conf on %s" % host)
        disable_gpgcheck = "echo gpgcheck=no >> /etc/yum.conf"

        stdin, stdout, stderr = ssh_c.ExecuteCmd(disable_gpgcheck)


    def run_repo_setup(self, options, conf_dict):
        """
        run async_updates repo function using threads per host.
        """

        threads = Threader()

        threads.gather_results([threads.get_item(self.install_yum_utils, \
                                host, conf_dict) for host in \
                                self.existing_nodes])

        if self.build_repo_tag:
            logger.log.info("BUILD_REPO_TAG found in env")
            threads.gather_results([threads.get_item(self.copy_build_repo, \
                                    host, conf_dict) for host in \
                                    self.existing_nodes])
        else:
            logger.log.info("BUILD_REPO_TAG not found in env")


        if options.build_repo:
            logger.log.info("Manual repo to be copied to resources.")
            self.build_repo = options.build_repo
            threads.gather_results([threads.get_item(self.my_build_repo, \
                                   host, conf_dict) for host in \
                                   self.existing_nodes])

        if "z-candidate" in self.brew_tag:
            logger.log.info("brew tag is for z-candidate, hence picking batched repo from conf.")
            threads.gather_results([threads.get_item(self.copy_async_updates_repo, \
                                    host, conf_dict) for host in \
                                    self.existing_nodes])
        else:
            logger.log.info("brew tag is not for z-candidate, hence not picking any batched repo from conf.")



        if self.task_repo_urls and self.static_repo_url:
            logger.log.info("STATIC_REPO_URLS from env variable is %s" % self.static_repo_url)
            logger.log.info("TASK_REPO_URLS from env variable is %s" % self.task_repo_urls)
            logger.log.info("Check and copy task_repo if dist is appropriate")
            threads.gather_results([threads.get_item(self.copy_task_repo, \
                                    host, conf_dict) for host in \
                                    self.existing_nodes])
        else:
            logger.log.info("TASK_REPO_URLS env variable not found")

        if self.static_repo_url:
            logger.log.info("Check and copy static_repo if dist is appropriate")
            threads.gather_results([threads.get_item(self.copy_static_repo, \
                                    host, conf_dict) for host in \
                                    self.existing_nodes])
        else:
            logger.log.info("STATIC_REPO_URLS env variable not found")

        if conf_dict.has_key('repos'):
            logger.log.info("repos section detected.")
            threads.gather_results([threads.get_item(self.create_repos_section, \
                                    host, conf_dict) for host in \
                                    self.existing_nodes])
        else:
            logger.log.info("repos section not found.")
