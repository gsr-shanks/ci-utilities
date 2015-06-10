Config sections
===============

* `beaker`_:
* `jenkins`_:
* `git`_:
* `gerrit`_:
* `errata`_:
* `brew`_:
* `async_repos`_:
* `triggers`_:
* `restraint`_:
* `restraint_jobs`_:
* `repos`_:

beaker
------

::

    [beaker]
    username = root
    password = whatever

This section supports username and password only. This username and password are
the credentials for your test resources. It is expected that all test
resources have a common username and password.


jenkins
-------

::

    [jenkins]
    job_name = 
    workspace = 
    existing_nodes = 
    jenkins_master_url = https://idm-qe-jenkins.ci.redhat.com

To start off, values for job_name, workspace, existing_nodes are empty. The
values are updated in the conf during runtime depending on Jenkins job. All 
these values are extracted from environment variables of the Jenkins job.

**Note:** If nexus is executed manually outside of Jenkins, then it is
expected that you export job_name, workspace and existing_nodes into the
environment or manually edit the conf file with appropriate values.

Since every job in Jenkins is unique, a lot depends on the job_name.


git
---

::

    [git]
    git_project = ipa-tests
    git_repo_url = git://git.redhat.com/ipa-tests.git
    git_get_branch = ci
    git_test_branch = default
    git_tar_out = ipa-tests.tar

Nexus git plugin uses git archive protocol to get the content in a .tar
format from git_get_branch. git_tar_out value is the name of the tar file.
Once the content is available, then it is untar'ed as git_project. 

This addresses the use case where your git repository is huge and you do not
intend to clone it everytime for few CI related files.

git_test_branch is used to update the fetch URL in restraint xml's. 'default'
leaves the restraint xml untouched, else the branch is appended in fetch URL.


gerrit
------

::

    [gerrit]
    gerrit_repo_url = https://foo.bar.com/gerrit/ipa-pytests


If GERRIT_REFSPEC is available in environment as variable then it is git
pulled on top of the cloned repository. This is useful if you plan to test
your patchset before merging it.

errata
------

::

    [errata]
    xmlrpc_url = http://err.redhat.com/xmlrpc
    download_devel = http://download.devel.redhat.com
    mount_base = /mnt/redhat
    build_download_loc = /tmp/errata-builds

As of now, this section entirely is to support the command line usage.


brew
----

::

    [brew]
    brew_root = http://download.redhat.com/brewroot
    brew_hub = http://brew.redhat.com/brewhub
    brew_builds = 
        ipa, sssd, pki-core, 389-ds-base, bind, bind-dyndb-ldap, nss,
        python-yubico, certmonger, python-nss, python-dns, nspr, samba
    brew_tag = rhel-7.1-candidate
    brew_arch = x86_64
    build_download_loc = /tmp/brew-builds

brew_root is used to contruct a downloadable URL of the brew builds provided 
in brew_builds. All the builds are downloaded parallely using threads. brew_tag 
and brew_arch are the values you need to provide as per your job or requirement.

By default, noarch rpm's are downloaded along with the arch provided at brew_arch.
The default download location of brew builds is /tmp/brew-builds which can be 
overwritten using the command line option as mentioned in "Command line usage" 
section of this documentation. 




async_repos
-----------

::
        
    [async_repos]
    7.1 = http://blah.redhat.com/nightly/latest-RHEL-7/Server/x86_64/os/


The above section is checked and used only if 'z-candidate' is found in
brew-tag of CI_MESSAGE.

nexus checks for the platform version on the test resources. '7.1' if found in
platform version, then a .repo is created for the test resource that matched
and then is copied over to /etc/yum.repos.d



triggers
--------

::

    [triggers]
    ipa-user-cli = ipa-user-cli-rhel71-x86_64-trigger
    ipa-group-cli = ipa-group-cli-rhel71-x86_64-trigger
    ipa-hbac-func = ipa-hbac-func-rhel71-x86_64-trigger
    ipa-password = ipa-password-rhel71-x86_64-trigger
    ipa-dns = ipa-dns-rhel71-x86_64-trigger

This section uses jenkins python api to trigger jobs from nexus cli.

restraint
---------

::

    [restraint]
    remove_rpm = rhts-python
    install_rpm = restraint staf restraint-rhts
    job_xml_loc = ipa-tests/restraint
    6.7 = http://blah.redhat.com/~bpeck/restraint/el6.repo
    7.2 = http://blah.redhat.com/~bpeck/restraint/el7.repo
    20 = http://blah.redhat.com/~bpeck/restraint/fc20.repo

nexus uninstall rpms provided at remove_rpm and installs rpms provided at
install_rpm. Restraint repo needs to be copied before installing the rpms,
hence, based on the platform version the .repo file is copied over to the test
resource.

job_xml_loc is the location where you store all your restraint xml jobs. This
is to avoid mentioning the base path name everytime.


restraint_jobs
--------------

::

    [restraint_jobs]
    ipa-adtrust-rhel71-x86_64-bkr-runtest = ipa-adtrust-rhel71-x86_64-bkr.xml
    ipa-sudo-rhel71-x86_64-bkr2-runtest = ipa-sudo-rhel71-x86_64-bkr.xml
    ipa-user-cli-rhel71-x86_64-bkr-runtest = ipa-user-cli-rhel71-x86_64-bkr.xml
    ipa-hbac-func-rhel71-x86_64-bkr3-runtest = ipa-hbac-func-rhel71-x86_64-bkr3.xml
    ipa-password-rhel71-x86_64-bkr-runtest = ipa-password-rhel71-x86_64-bkr.xml

restraint_jobs section maps the Jenkins environments' JOB_NAME to the
restraint xml located in restraint sections job_xml_loc. Nexus gets the job
name from enrionment variable and looks for the appropriate restraint xml
file.

Cheat: You may skip mapping JOB_NAME to restraint xml in this section by
exporting environment variable as WHAT_TEST="restraint xml file name"

repos
-----

Any value you have in this section, is used as baseurl while creating yum repo
using yum-config-manager command in all the existing nodes.
