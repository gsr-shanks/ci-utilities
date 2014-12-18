#!/usr/bin/python

import os
import sys
import ConfigParser
import time
import util
import json
from common.nodes import ExistingNodes

class SetupConfig():

    def workspace_dir(self, x):
        self.workspace = x

        idm_config = ConfigParser.SafeConfigParser()
        idm_config.read("etc/global.conf")
        util.log.info (idm_config.sections())

        workspace = os.environ.get(self.workspace)
        if not workspace:
            util.log.error("Failed to find %s env variable." % self.workspace)
            sys.exit(1)
        else:
            util.log.info("WORKSPACE env variable is %s." % workspace)

        idm_config.set('global', 'workspace', workspace)
        with open('etc/global.conf', 'wb') as idm_setup_config:
            idm_config.write(idm_setup_config)
        return workspace

    def jenkins_job_name(self, x):
        self.jobname = x

        idm_config = ConfigParser.SafeConfigParser()
        idm_config.read("etc/global.conf")
        util.log.info (idm_config.sections())
        job_name = os.environ.get(self.jobname)
        if not job_name:
            util.log.error("Failed to find %s env variable." % self.jobname)
            sys.exit(1)
        else:
            util.log.info("%s is my job." % job_name)

        idm_config.set('global', 'job_name', job_name)

        with open('etc/global.conf', 'wb') as idm_setup_config:
            idm_config.write(idm_setup_config)
        return job_name

    def ci_message(self, x):
        self.ci_message = x

        ci_msg = os.environ.get("CI_MESSAGE")
        data = json.loads(ci_msg)
        print(json.dumps(data, indent=4))

        with open('ci_message.json', 'w') as outfile:
            json.dump(data, outfile, indent=4)

        ci_msg_value = data[self.ci_message]
        return ci_msg_value
