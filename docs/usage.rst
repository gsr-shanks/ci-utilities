Command line usage
==================

Note: Options provided in commandline overrides config values, which also
means if the options are not provided in commandline then it is assumed that
it is available in the configuration file.

* `jenkins`_:
* `git`_:
* `errata`_:
* `brew`_:
* `restraint`_:
* `ci`_:

jenkins
-------

::

    ~$ nexus --conf workspace/my.conf jenkins --show-triggers

Displays all the triggers available for your configuration.

::

    ~$ nexus --conf workspace/my.conf jenkins --run $JOB_NAME

This command triggers any jenkins job in your Jenkins master.


git
---

::

    ~$ nexus --conf ~/projects/nexus/nexus/etc/nexus.conf git --project ipa-tests
        --repo git://git.app.eng.bos.redhat.com/ipa-tests.git --branch ci --tar
        ipa-tests.tar

This command archives the git repo and then downloads the content in a tar
format. There maybe repos which are huge in size, in such situations it makes
perfect sense to use the git archive protocol.


errata
------

::

    ~$ nexus --conf my.conf errata --errata-id 19947 --errata-loc /tmp/err

This command downloads all the builds attached to a specific erratum. The
--errata-loc is optional here, by default, the location is picked from the
build_download_loc of errata section in conf.


brew
----

::

    ~$ nexus --conf my.conf brew --tag rhel-7.1-candidate --build ipa --arch
        x86_64 --loc /tmp/brew-builds

This command downloads the build as per the options specified. Irrespective of
which arch you provide noarch is downloaded by default. Instead of
commandline, all this options can be mentioned in the conf as well.


restraint
---------

Pre-requisitie to execute this command:

- JOB_NAME - export in environment variable or set it in conf.
- EXISTING_NODES - export in environment variable or set it in conf.
- WORKSPACE - export in evn var or set it in conf.


In your restraint xml::

    <param name="MASTER" value="hostname1"/>

Note the value "hostname1", when restraint command is executed then
"hostname1" value is replaced with the first hostname from EXISTING_NODES
environment variable. 

In your restraint.xml for multi host testing::

    <param name="MASTER" value="hostname1"/>
    <param name="MASTER" value="hostname2"/>

In your restraint.xml if you have <task name="/ipa-server/master/ipa-cert">
then, "/master/" gets replaced with the git_test_branch value from conf.
However, having 'default' in git_test_branch will leave the restraint xml
untouched.

::

    ~$ nexus --conf my.conf restraint --restraint-xml ipa-tests/restraint/ipa-sudo-rhel71-x86_64-bkr.xml

You may also provide a repo file to restraint command which is to be copied to
test resources.

::

    ~$ nexus --conf my.conf restraint --build-repo /home/shanks/my_repo.repo 
        --restraint-xml ipa-tests/restraint/ipa-sudo-rhel71-x86_64-bkr.xml


ci
--

::

    ~$ nexus --conf my.conf ci --provisioner beaker --framework restraint

One command to be used in Continuous Integration enviroment for all the
Jenkins jobs. This command is to be used *ONLY* when triggered through CI plugin.
