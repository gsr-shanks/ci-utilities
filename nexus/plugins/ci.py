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


from nexus.lib import logger
from nexus.lib import factory
from nexus.plugins.brew import Brew
from nexus.plugins.git import Git
from nexus.plugins.restraint import Restraint
from nexus.plugins.repos import Repos
from nexus.plugins.pytests import Pytest
from nexus.plugins.testcoverage import Testcoverage
from nexus.plugins.dogtag import PkiTest
import os

class CI():

    def __init__(self, options, conf_dict):
        self.provisioner = options.provisioner
        self.framework = options.framework

    def run(self, options, conf_dict):
        if self.provisioner == "beaker" and self.framework == "restraint":
            git = Git(options, conf_dict)
            git.get_archive()

            repo = Repos(options, conf_dict)
            repo.run_repo_setup(options, conf_dict)

            restraint = Restraint(options, conf_dict)

            """ This function actually runs restraint command and
            executed the job on beaker.
            """
            restraint.run_restraint(options, conf_dict)

        elif self.provisioner == "beaker" and self.framework == "pytest":

            repo = Repos(options, conf_dict)
            repo.run_repo_setup(options, conf_dict)

            pytest = Pytest(options, conf_dict)
            pytest.run_pytest(options, conf_dict)

            if options.coverage is True:
                logger.log.info("Get coverage report")
                coverage = Testcoverage(options, conf_dict)
                coverage.coverage_reports(options, conf_dict)
                coverage.get_reports(options, conf_dict)
            else:
                logger.log.info("No coverage report since option not set")

        elif self.provisioner == "openstack" and self.framework == "pytest":

            repo = Repos(options, conf_dict)
            repo.run_repo_setup(options, conf_dict)

            pytest = Pytest(options, conf_dict)
            pytest.run_pytest(options, conf_dict)

            if options.coverage is True:
                logger.log.info("Get coverage report")
                coverage = Testcoverage(options, conf_dict)
                coverage.coverage_reports(options, conf_dict)
                coverage.get_reports(options, conf_dict)
            else:
                logger.log.info("No coverage report since option not set")

        elif self.provisioner == "openstack" and self.framework == "restraint":

            git = Git(options, conf_dict)
            git.get_archive()

            repo = Repos(options, conf_dict)
            repo.run_repo_setup(options, conf_dict)

            restraint = Restraint(options, conf_dict)
            restraint.run_restraint(options, conf_dict)

        elif self.provisioner == "openstack" and self.framework == "dogtag-pytest":
            repo = Repos(options, conf_dict)
            repo.run_repo_setup(options, conf_dict)
            pkitest = PkiTest(options, conf_dict)
            pkitest.set_hostnames()
            pkitest.update_etc_hosts()
            yaml_file = pkitest.create_yaml()
            logger.log.info("we completed creating yaml file")
            logger.log.info("Current working directory is: %s"%(os.environ.get('PWD')))
            pkitest.deploy_ssh_keys()
            if pkitest.copy_extras_repo():
                logger.log.info("Extra's repo configured successfull")
                if pkitest.install_prereqs():
                    logger.log.info("Pre-requisites to run pytest has been installed successfull")
                    pkitest.pytest_setup()
                    if pkitest.run_pytest(yaml_file):
                        logger.log.info("pytest ran successfully")
                    else:
                        logger.log.info("pytest failed")
                else:
                    logger.log.info("Pre-requisites to run pytest has not been installed")
            else:
                logger.log.info("Extras repo did not configure")

        elif self.provisioner == "beaker" and self.framework == "dogtag-pytest":
            repo = Repos(options, conf_dict)
            repo.run_repo_setup(options, conf_dict)
            pkitest = PkiTest(options, conf_dict)
            pkitest.update_etc_hosts()
            yaml_file = pkitest.create_yaml()
            pkitest.deploy_ssh_keys()
            if pkitest.copy_extras_repo():
                logger.log.info("Extra's repo configured successfull")
                if pkitest.install_prereqs():
                    logger.log.info("Pre-requisites to run pytest has been installed successfull")
                    if pkitest.run_pytest(yaml_file):
                        logger.log.info("pytest ran successfully")
                    else:
                        logger.log.info("pytest failed")
                else:
                    logger.log.info("Pre-requisites to run pytest has not been installed")
            else:
                logger.log.info("Extras repo did not configure")
        else:
            logger.log.error("Unknown provisioner or framework")
