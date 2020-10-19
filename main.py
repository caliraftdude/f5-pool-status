#!/usr/bin/python
########################################################################################
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files(the "Software"), to deal in the Software 
# without restriction, including without l > imitation the rights to use, copy, modify, 
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to 
# permit persons to whom the Software is furnished to do so, subject to the following 
# conditions:
#
# The above copyright notice and this permission notice shall be included in all 
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A 
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
# CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
# OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
########################################################################################
# f5-pool-state
#
# author:   Dan Holland
# date:     2020.10.16
# purpose:  This is a simple script that uses iRest to query the status of pool members
#           and then optionally compare to a previous list of collected state
########################################################################################

import sys
import os
import logging
import getpass
import platform
import subprocess
#from datetime import datetime

from f5.bigip import ManagementRoot
import icontrol.exceptions
import f5.sdk_exception


# The object library will be the library that has all the configuration data in it.  The top level object is a dictionary that uses
# the above list as a key to the type of object.  That will always lead to a list of dictionaries.  The dictionaries in the list are
# the configuration data of each instance of said object
OBJECT_LIBRARY = {}

# Use these for accessing the bigip - not sure how the tf file should use these..
USERNAME = ""
PASSWORD = ""

f_printEmptyPools = False

#################################################################
#   Main program
#################################################################
def main():
    global USERNAME
    global PASSWORD
    test = 0

    if not test:
        USERNAME = getpass.getpass(prompt="Username:\t")
        PASSWORD = getpass.getpass(prompt="Password:\t")
        try:
            # Python 2.x
            DEVICE = raw_input("IP Address of device to copy config from: ")
        except NameError:
            # Python 3.x
            DEVICE = input("IP Address of device to copy config from: ")
    else:
        USERNAME = "admin"
        PASSWORD = "admin"
        DEVICE = "10.1.1.100"

    # connect to the BigIP
    try:
        if not check_ping(DEVICE):
            log.exception("Unable to ping IP of device")
            sys.exit(-1)

        MGMT = ManagementRoot(DEVICE, USERNAME, PASSWORD)

    except icontrol.exceptions.iControlUnexpectedHTTPError:
        log.exception("Critical failure during login, failed to obtaion Managment Obj")
        sys.exit(-1)

    parsePools(MGMT)
    log.info("Device successfully parsed...")

    printObjectLibrary()


    # Create output directory
    #try:
    #    path = os.getcwd()
    #    path += "/TF-" + DEVICE
    #    if os.path.exists(path):
    #        t = datetime.now()
    #        path += '-{}{}{}-{}:{}:{}'.format(t.year, t.month, t.day, t.hour, t.minute, t.second)
    #    os.mkdir(path)
    #    path += "/"

    #    except OSError:
    #    log.exception("Unable to create output directory (permissions issue?)")


def parsePools(MGMT):
    try:
        # Get the collection of pool objects
        collection = eval('MGMT.tm.ltm.pools.get_collection()')
            
    except (f5.sdk_exception.LazyAttributesRequired, AttributeError):
        log.critical("Possible unnamed resource in the tree.  LazyAttributesRequired or AttributeError exception thrown")
        exit
    except:
        log.critical("unhandled exception thrown")
        exit

    # Parse the members for each of the pools
    for pool_obj in collection:
        # For each pool: Create entry in dictionary, and walk through the pool members
        member_list = []
        members = pool_obj.members_s.get_collection()
        for member in members:
            member_list_element = [member.name, member.state]
            member_list.append(member_list_element)

        OBJECT_LIBRARY[pool_obj.fullPath] = member_list

def printObjectLibrary():
    print(f"POOL{'':41}POOL MEMBER{'':39}STATUS{'':4}")
    print("==========================================================================================================")

    for pool in sorted(OBJECT_LIBRARY):
        if not OBJECT_LIBRARY[pool]:
            print(f"{pool:45}{'EMPTY':50}")
        for members in OBJECT_LIBRARY[pool]:
            print(f"{pool:45}{members[0]:50}{members[1]:10}")
                   
#################################################################
#   Misc utility Functions
#################################################################
def getLogging():
    FORMAT = '%(asctime)-15s %(levelname)s\tFunc: %(funcName)s():\t%(message)s'
    logging.basicConfig(format=FORMAT)
    return logging.getLogger('f5-pool-status')

# Returns True if host responds to a ping request.
def check_ping(address):
    # Deal with Windows vs Linux differences with ping
    param = '-n' if platform.system().lower()=='windows' else '-c'

    # Build out command.  Moving to subprocess which avoids potential shell.injection issues
    command = ['ping', param, '1' , address]

    # Open a pipe to /dev/null to squash output and make the call
    with open(os.devnull, 'w') as FNULL:
        return subprocess.call(command, stdout=FNULL, stderr=subprocess.STDOUT) == 0

#################################################################
#   Entry point
#################################################################
if __name__ == "__main__":
    # Get logging object
    log = getLogging()
    log.setLevel(logging.ERROR)

    main()
