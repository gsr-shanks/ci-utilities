#!/usr/bin/python

import koji as brew
import threading
import ConfigParser
import json
import urllib2
import os
import paramiko
import socket
import argparse

class Conf_ini(ConfigParser.ConfigParser):
    def conf_to_dict(self):
        """
        Reading a config file into a dictionary.

        In config, you all the items in dictionary, the issue is that you can't
        use it as is. The default data structure is OrderedDict. The k holds the
        section name. The next code creates a dictionary based on _defaults
        OrderedDict(). And for the **d[k], it means that d[k] (dictionary) is
        decomposed into assignments. This is necessary as the dict() method
        requires assignments as additional parameters to the method.
        """
        d = dict(self._sections)
        for k in d:
            d[k] = dict(self._defaults, **d[k])
            d[k].pop('__name__', None)
        return d

class Threader(object):

    def get_item(self, f, item):
        """
        Function which runs a given function in a thread and stores the result.
        """
        result_info = [threading.Event(), None]
        def runit():
            result_info[1] = f(item)
            result_info[0].set()
        threading.Thread(target=runit).start()
        return result_info

    def gather_results(self, result_info):
        """
        Function to gather the results from get_item.
        """
        results = []
        for i in xrange(len(result_info)):
            result_info[i][0].wait()
            results.append(result_info[i][1])
        return results

class SSHClient(paramiko.SSHClient):
    """ This class Inherits paramiko.SSHClient and implements client.exec_commands
    channel.exec_command """

    def __init__(self, conf_dict, hostname=None, port=None, username=None, password=None):
        """ Initialize connection to Remote Host using Paramiko SSHClient. Can be
        initialized with hostname, port, username and password.
        if username or passwod is not given, username and password will be taken
        from etc/nexus.ini
        """
        self.hostname = hostname

        if port == None:
            self.port = 22
        else:
            self.port = port
        if username == None or password == None:
            self.username = conf_dict['beaker']['username']
            self.password = conf_dict['beaker']['password']
        else:
            self.username = username
            self.password = password

        paramiko.SSHClient.__init__(self)
        self.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.connect(self.hostname, port=self.port, username=self.username, password=self.password, timeout=30)
        except (paramiko.AuthenticationException, paramiko.SSHException, socket.error):
            raise

    def ExecuteCmd(self, args):
        """ This Function executes commands using SSHClient.exec_commands().
        @params: args: Commands that needs to be executed. Commands which have longer
        outputs or data is buffered should not be excuted using this function. Use ExecuteScript
        function"""
        try:
            stdin, stdout, stderr = self.exec_command(args,timeout=30)
        except paramiko.SSHException, e:
            print "Cannot execute %s", args
            raise
        else:
            return stdin, stdout, stderr

    def ExecuteScript(self, args):
        """ This Function Executes commands/scripts using channel.exec_command().
        @params args: Commands/scripts that need to be executed.
        Data received from the command are buffered. """

        transport = self.get_transport()
        stdout = StringIO.StringIO()
        stderr = StringIO.StringIO()
        try:
            channel = transport.open_session()
        except paramiko.SSHException, e:
            print "Session rejected"
            raise
        try:
            channel.exec_command(args)
        except  paramiko.SSHException, e:
            print "Cannot execute %s", args
            channel.close()
        else:
            while not channel.exit_status_ready():
                if channel.recv_ready():
                    data = channel.recv(1024)
                    while data:
                        stdout.write(data)
                        data = channel.recv(1024)
                if channel.recv_stderr_ready():
                    error_buff = channel.recv_stderr(1024)
                    while error_buff:
                        stderr.write(error_buff)
                        error_buff = channel.recv_stderr(1024)

            exit_status = channel.recv_exit_status()

        return stdout,stderr,exit_status

    def CopyFiles(self,source,destination):
        """ This Function copies files to destination nodes
        @param:
        source: name of the file toe be copied
        destination: name of file to be saved at the destination node
        """
        Transport = self.get_transport()
        sftp = paramiko.SFTPClient.from_transport(Transport)
        FileAttributes = sftp.put(source, destination)
        return FileAttributes
