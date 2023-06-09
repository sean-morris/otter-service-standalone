#!/bin/bash
# These are the most common notebooks out there 
# If you load this first then users cna quickly grade
# notebooks 
/etc/venv-otter4/bin/python3 -m otter grade -a /etc/otter-service-stdalone/autograder.zip -p /etc/otter-service-stdalone/notebooks
/etc/venv-otter3/bin/python3 -m otter grade -a /etc/otter-service-stdalone/autograder-3.3.0.zip -p /etc/otter-service-stdalone/notebooks-3.3.0
otter_service_stdalone