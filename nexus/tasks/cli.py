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
import yum
import argparse
import ConfigParser
from nexus.lib import logger
from nexus.lib import factory
from nexus.plugins.brew import Brew
from nexus.plugins.restraint import Restraint
from nexus.plugins.errata import Errata
from nexus.plugins.git import Git
from nexus.plugins.ci import CI
from nexus.plugins.my_jenkins import Jenkins
from nexus.lib.ci_message import CI_MSG
import nexus.version

def create_parser():
    parser = argparse.ArgumentParser()
    recursive_parser = argparse.ArgumentParser(add_help=False)

    subparser = parser.add_subparsers(help='git, brew, errata, restraint, ci \
        beaker, openstack, pytest or jenkins', dest='command')

    parser_git = subparser.add_parser('git')
    parser_git.add_argument('--project', help='Git project')
    parser_git.add_argument('--repo', help='Git repo URL')
    parser_git.add_argument('--branch', help='Git branch')
    parser_git.add_argument('--tar', help='Git archived file out')
    parser_git.add_argument('--show-triggers', help=argparse.SUPPRESS)

    parser_brew = subparser.add_parser('brew')
    parser_brew.add_argument('--tag', help='Brew build tag')
    parser_brew.add_argument('--build', help='Brew build name')
    parser_brew.add_argument('--arch', help='Machine arch. Defaults to all if \
                            not provided')
    parser_brew.add_argument('--loc', help='Absolute path of download to \
                            directory')
    parser_brew.add_argument('--show-triggers', help=argparse.SUPPRESS)

    parser_errata = subparser.add_parser('errata')
    parser_errata.add_argument('--errata-id', help='Errata Id')
    parser_errata.add_argument('--errata-loc', help='Absolute path of download \
                                to directory')
    parser_errata.add_argument('--show-triggers', help=argparse.SUPPRESS)

    parser_restraint = subparser.add_parser('restraint')
    parser_restraint.add_argument('--build-repo', help='.repo file which you \
                                    would like to copy to test resources')
    parser_restraint.add_argument('--restraint-xml', help='Restraint xml file')
    parser_restraint.add_argument('--show-triggers', help=argparse.SUPPRESS)

    parser_jenkins = subparser.add_parser('jenkins')
    parser_jenkins.add_argument('--run', help='Build Jenkins job')
    parser_jenkins.add_argument('--show-triggers', action='store_true', help='Show triggers from conf')

    parser_pytest = subparser.add_parser('pytest')

    parser_beaker = subparser.add_parser('beaker')
    parser_openstack = subparser.add_parser('openstack')

    parser_ci = subparser.add_parser('ci')
    parser_ci.add_argument('--provisioner', help='Infra used for test systems \
                            provisioning')
    parser_ci.add_argument('--framework', help='Test automation framework')
    parser_ci.add_argument('--coverage', action='store_true', help='Test automation coverage')
    parser_ci.add_argument('--project', help=argparse.SUPPRESS)
    parser_ci.add_argument('--repo', help=argparse.SUPPRESS)
    parser_ci.add_argument('--branch', help=argparse.SUPPRESS)
    parser_ci.add_argument('--tar', help=argparse.SUPPRESS)
    parser_ci.add_argument('--build-repo', help=argparse.SUPPRESS)
    parser_ci.add_argument('--restraint-xml', help=argparse.SUPPRESS)
    parser_ci.add_argument('--show-triggers', help=argparse.SUPPRESS)
    parser_ci.add_argument('--run', help=argparse.SUPPRESS)


    parser.add_argument('--conf', dest='conf', help='configuration file')
    parser.add_argument('--version', dest='version', action='version', \
                        version=version(),
                        help='show version')

    return parser

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = create_parser()
    options = parser.parse_args(argv)
    if not options.command:
        parser.error("Must specify a 'command' to be performed")

    config = setup_conf(options)
    execute(options, config)

def setup_conf(options):

    conf = options.conf

    config = ConfigParser.SafeConfigParser()
    config.read(conf)

    ci_msg = CI_MSG()
    t = ci_msg.get_ci_msg_value('tag')
    if t:
        tag = t['name']
        config.set('brew', 'brew_tag', tag)
        logger.log.info("brew tag name is %s" % tag)
    else:
        logger.log.warn("tag not found in CI_MESSAGE")

    workspace = os.environ.get("WORKSPACE")
    if not workspace:
        logger.log.warn("Unable to find WORKSPACE env variable")
    else:
        logger.log.info("WORKSPACE env variable is %s" % workspace)
        config.set('jenkins', 'workspace', workspace)

    job_name = os.environ.get("JOB_NAME")
    if not job_name:
        logger.log.warn("Unable to find JOB_NAME env variable")
    else:
        logger.log.info("JOB_NAME from env variable is %s" % job_name)
        config.set('jenkins', 'job_name', job_name)

    existing_nodes = os.environ.get("EXISTING_NODES")
    if not existing_nodes:
        logger.log.warn("Unable to find EXISTING_NODES env variable")
    else:
        logger.log.info("EXISTING_NODES from env variable is %s" % existing_nodes)
        config.set('jenkins', 'existing_nodes', existing_nodes)

    private_ips = os.environ.get("PRIVATE_IPS")
    if not private_ips:
        logger.log.warn("Unable to find PRIVATE_IPS env variable")
    else:
        logger.log.info("PRIVATE_IPS from evn variable is %s" % private_ips)
        config.set('jenkins', 'private_ips', private_ips)

    with open(conf, 'wb') as confini:
        config.write(confini)

    if os.path.isfile(conf):
        f = factory.Conf_ini()
        f.read(conf)
        logger.log.info("Writing environment details to %s" % conf)
        conf_dict = f.conf_to_dict()
        return conf_dict

def execute(options, conf_dict):

    yb = yum.YumBase()

    if options.command == 'git':
        if yb.rpmdb.searchNevra(name='git'):
            logger.log.info("Git rpm found.")

            git = Git(options, conf_dict)
            git.get_archive()
        else:
            logger.log.error("Git rpm not installed.")
            sys.exit(2)

    elif options.command == 'beaker':
        if yb.rpmdb.searchNevra(name='beaker-client'):
            logger.log.info("beaker-client rpm found")

            beaker = Beaker(options, conf_dict)
            beaker.run(options, conf_dict)
        else:
            logger.log.error("beaker-client rpm not found")
            sys.exit(2)

    elif options.command == 'brew':
        if yb.rpmdb.searchNevra(name='koji'):
            logger.log.info("Koji rpm found.")

            brew = Brew(options, conf_dict)
            brew.get_latest(options, conf_dict)
        else:
            logger.log.error("Koji rpm not installed.")
            sys.exit(2)

    elif options.command == 'restraint':
        if yb.rpmdb.searchNevra(name='restraint-client'):
            logger.log.info("restraint-client rpm found.")
            restraint = Restraint(options, conf_dict)
            restraint.run_restraint(options, conf_dict)
            restraint.restraint_junit()
        else:
            logger.log.error("restraint-client rpm not installed.")
            sys.exit(2)

    elif options.command == 'errata':
        errata = Errata(options, conf_dict)
        errata.download_errata_builds()
    elif options.command == 'jenkins':
        jenkins = Jenkins(options, conf_dict)
        jenkins.main(options, conf_dict)
    elif options.command == 'ci':
        ci = CI(options, conf_dict)
        ci.run(options, conf_dict)

def version():
    return "version: %s" % nexus.version.version_info.version_string()

if __name__ == '__main__':
    main()
