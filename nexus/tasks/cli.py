#!/usr/bin/python

import os
import sys
import argparse
import ConfigParser
from nexus.lib import logger
from nexus.lib import factory
from nexus.plugins.brew import Brew
from nexus.plugins.restraint import Restraint
from nexus.plugins.errata import Errata
from nexus.plugins.git import Git
from nexus.plugins.ci import CI
import nexus.version

def create_parser():
    parser = argparse.ArgumentParser()
    recursive_parser = argparse.ArgumentParser(add_help=False)

    subparser = parser.add_subparsers(help='git, brew, errata, restraint or ci',
                                      dest='command')

    parser_git = subparser.add_parser('git')
    parser_git.add_argument('--project', help='Git project')
    parser_git.add_argument('--repo', help='Git repo URL')
    parser_git.add_argument('--branch', help='Git branch')
    parser_git.add_argument('--tar', help='Git archived file out')

    parser_brew = subparser.add_parser('brew')
    parser_brew.add_argument('--tag', help='Brew build tag')
    parser_brew.add_argument('--build', help='Brew build name')
    parser_brew.add_argument('--arch', help='Machine arch. Defaults to all if not provided')
    parser_brew.add_argument('--loc', help='Absolute path of download to directory')

    parser_errata = subparser.add_parser('errata')
    parser_errata.add_argument('--errata-loc', help='Absolute path of download to directory')

    parser_restraint = subparser.add_parser('restraint')
    parser_restraint.add_argument('--build-repo', help='Build repo')
    parser_restraint.add_argument('--restraint-xml', help='Restraint xml file')

    parser_ci = subparser.add_parser('ci')
    parser_ci.add_argument('--provisioner', help='Infra used for test systems provisioning')
    parser_ci.add_argument('--builds-from', help='Builds from brew or errata')
    parser_ci.add_argument('--project', help=argparse.SUPPRESS)
    parser_ci.add_argument('--repo', help=argparse.SUPPRESS)
    parser_ci.add_argument('--branch', help=argparse.SUPPRESS)
    parser_ci.add_argument('--tar', help=argparse.SUPPRESS)
    parser_ci.add_argument('--build-repo', help=argparse.SUPPRESS)
    parser_ci.add_argument('--restraint-xml', help=argparse.SUPPRESS)


    parser.add_argument('--conf', dest='conf', help='configuration file')
    parser.add_argument('--version', dest='version', action='version', version=version(),
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

    workspace = os.environ.get("WORKSPACE")
    if not workspace:
        logger.log.warn("Unable to find WORKSPACE in env variable")
    else:
        logger.log.info("WORKSPACE env variable is %s" % workspace)
        config.set('jenkins', 'workspace', workspace)

    job_name = os.environ.get("JOB_NAME")
    if not job_name:
        logger.log.warn("Unable to find JOB_NAME in env variable")
    else:
        logger.log.info("JOB_NAME from env variable is %s" % job_name)
        config.set('jenkins', 'job_name', job_name)

    existing_nodes = os.environ.get("EXISTING_NODES")
    if not existing_nodes:
        print ("Failed to find EXISTING_NODES env variable.")
    else:
        print ("EXISTING_NODES from env variable is %s" % existing_nodes)
        config.set('jenkins', 'existing_nodes', existing_nodes)

    with open(conf, 'wb') as confini:
        config.write(confini)

    if os.path.isfile(conf):
        f = factory.Conf_ini()
        f.read(conf)
        conf_dict = f.conf_to_dict()
        return conf_dict

def execute(options, conf_dict):

    if options.command == 'git':
        git = Git(options, conf_dict)
        git.get_archive()
    elif options.command == 'brew':
        brew = Brew(options, conf_dict)
        brew.get_latest(options, conf_dict)
    elif options.command == 'restraint':
        restraint = Restraint(options, conf_dict)
        restraint.run_restraint(options, conf_dict)
        restraint.restraint_junit()
    elif options.command == 'errata':
        errata = Errata(options, conf_dict)
        errata.download_errata_builds()
    elif options.command == 'ci':
        ci = CI(options, conf_dict)
        ci.run(options, conf_dict)

def version():
    return "version: %s" % nexus.version.version_info.version_string()

if __name__ == '__main__':
    main()
