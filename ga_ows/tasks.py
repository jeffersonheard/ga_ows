#!/usr/bin/python

from celery.decorators import task
import os
import datetime
from django.contrib.gis.geos import GEOSGeometry
import csv
from django.db import connections, transaction

# create tasks here.  all tasks need to be decorated with @task.  Otherwise they are just regular functions. 
# They should probably ignore output as well, which is done by using @task(ignore_output=True)
#
# You can read more about tasks at http://www.celeryproject.org

