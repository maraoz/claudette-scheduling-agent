#!/bin/bash
# usage: watch.sh <your_command> <sleep_duration>

# I hate Mac OS X
while :; 
  do
  date
  $1
  date
  sleep $2
done