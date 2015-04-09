#!/usr/bin/python
# Copyright (c) 2014 Red Hat, Inc. All rights reserved.
#
# This copyrighted material is made available to anyone wishing
# to use, modify, copy, or redistribute it subject to the terms
# and conditions of the GNU General Public License version 2.
#
# This program is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public
# License along with this program; if not, write to the Free
# Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
# Boston, MA 02110-1301, USA.

""" This tool finds and gets the restraint repo based on the \
 Operating System version"""

import platform
from BeautifulSoup import BeautifulSoup 
import urllib2
import re
import requests

version = platform.dist()
print  version
reg = version[1:2]
number = " ".join(reg)

page = urllib2.urlopen("http://file.bos.redhat.com/~bpeck/restraint/")
soup = BeautifulSoup(page)

for link in soup.findAll('a', href=re.compile(str(int(float(number))))):
    target_link = "http://file.bos.redhat.com/~bpeck/restraint/" + link['href']
    if 'repo' in target_link:
        print "Downloading", target_link
        resp = requests.get(target_link)
        print resp
        if resp.status_code == 200:
            with open("/etc/yum.repos.d/restraint.repo", "w") as f:
                f.write(resp.content)
                print "Repo file stored in /etc/yum.repos.d/restraint.repo"
