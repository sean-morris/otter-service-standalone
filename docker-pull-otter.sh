#!/bin/bash
while (! docker stats --no-stream ); do
  echo "Waiting for Docker to launch..."
  sleep 1
done
# These are the most common notebooks out there 
# If you load this first then users cna quickly grade
# notebooks 
docker pull ucbdsinfra/otter-grader:3.3.0
docker pull ucbdsinfra/otter-grader:v4.2.1
