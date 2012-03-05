#!/usr/bin/env python

# Geoanalytics django app packaging script.  This should be pretty universal.
# If you can't follow these conventions, be really sensible about what you're
# doing.  This script picks up any items in the web/ directory and puts it in
# GEOANALYTICS_ROOT/geoanalytics-web.  It furthermore picks up any items in the
# bin/ directory and puts them in GEOANALYTICS_ROOT/geoanalytics-bin, and it
# finally puts all fixtures/ items in GEOANALYTICS_ROOT/geoanalytics-fixtures
# (these still have to be run upon being installed, although we might take care
# of that in the future).  In addition, all non python files within the source
# trees listed in "packages". Simply specify all the relevant parameters here
# and they'll be propagated down as long as you're following my directory
# conventions.  Also, be sure that the template loader in django knows how to
# get to app-level templates.  You might need to add the egg loader if you
# haven't already.

####### EDIT BELOW THIS LINE ##################################################

name = 'ga_ows'
version = '0.2'
packages = ['ga_ows', 'ga_ows.views', 'ga_ows.rendering', 'ga_ows.models']
author = 'Jeff Heard'
author_email = 'jeff@renci.org'
description = 'Geoanalytics core application for OGC webservices'
url = 'http://geoanalytics.renci.org'

####### DO NOT EDIT BELOW THIS LINE UNLESS YOU CAN'T HELP IT ##################

import os

try:
    from setuptools import setup
except:
    from distutils.core import setup


package_data = {}
for package in packages:
    packagepath = package.replace('.','/')   
    cwd = os.getcwd()
    os.chdir(packagepath)
    non_pyfiles = [line.strip() for line in os.popen('find -type f | egrep -v "py.*$"').readlines()]
    os.chdir(cwd)
    package_data[package] = non_pyfiles

setup(
    name=name,
    version=version,
    packages=packages,
    author=author,
    author_email=author_email,
    description=description,
    zip_safe=False,
    package_data = package_data, 
    include_package_data = True
)
