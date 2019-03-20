# Artificial-Satellite-Monitor-Gateway

Introduction:
A Python network application that functioned as an artificial satellite monitor gateway. It would receive zip code and satellite identifier as input parameters, make queries to Space-Track and NOAA API, calculate satellite visibility data/times in zip code area, then give notifications.

Libraries used:
sys, math, ephor, uszipcode, datetime, requests, twilio, RPi.GPIO, os, time

How to run:
Put the file icu.py with example.mp3 into the same folder
python3 -z [zipcode] -s [satellite id]
