#!/bin/bash
# These are the most common notebooks out there 
# If you load this first then users can quickly grade
# notebooks 
otter grade -a /etc/otter-service-stdalone/autograder.zip -p /etc/otter-service-stdalone/notebooks
otter_service_stdalone