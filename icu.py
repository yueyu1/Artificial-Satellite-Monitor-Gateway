#!/usr/bin/env python3

import sys
import math
import ephem
from uszipcode import ZipcodeSearchEngine
import datetime
import requests
#from twilio.rest import TwilioRestClient
#import RPi.GPIO as GPIO
import os
import time as sleepy

# function to handle requests status codes
def debug_respond_status(status):
    # good status
    if status == 200:
        print ("OK!")
    else:
        # status is not good, determine why and quit
        print ("Error!")
        if status == 301:
            print ("The server is redirecting you to a different endpoint!")
        if status == 401:
            print ("The server thinks you are not authenticated!")
        if status == 400:
            print ("The server thinks you made a bad request!")
        if status == 403:
            print ("The resource you're trying to access is forbidden!")
        if status == 404:
            print ("The resource you tried to access wasn't found on the server!")
        sys.exit(1)

##print("[x] Initializing GPIO...", end='')
### GPIO setup
##try:
##    GPIO.setwarnings(False)
##    GPIO.setmode(GPIO.BCM)
##    GPIO.setup(6, GPIO.OUT)
##except:
##    print("Error: GPIO initialization failed")
##    sys.exit(1)

##print("OK!")
##print("[x] Initiating twilio (SMS) client....", end='')
##
### setup twilio client
##try:
##    client = TwilioRestClient("AC3a8d804cf2129b61d794a13284a5921a", "f4b70a595cc6cdaa93ae2b2a519a584c")
##except:
##    print("Error: failed to create Twilio client")
##    sys.exit(1)

##print("OK!")

print("[x] Parsing command line arguments...",end='')

# command line parse start #

# get command line args
argc = len(sys.argv)
argv = sys.argv

cmdline = {"-z": 0, "-s": 1}
args = ["", ""]

# possible valid command line lengths
if (argc != 5):
    print("Error: Invalid command.")
    sys.exit(1)

# process tokens
for i in range(1, argc, 2):
    if argv[i] in cmdline:
        if args[cmdline[argv[i]]] != "":
            print("Error: Invalid command.")
            sys.exit(1)
        args[cmdline[argv[i]]] = argv[i + 1]
    else:
        print("Error: invalid command.")
        sys.exit(1)

# make sure mandatory args are present
if (args[0] == "") or (args[1] == ""):
    print("Error: Invalid command.")
    sys.exit(1)

# end of command line parse #

print("OK!")

# extract values from parsed command line
zipcode = args[0]
sat_id = args[1]

# space track login information
space_user = "yyue@vt.edu"
space_pass = "NETappsNETapps1234"

spacebaseURL = 'https://www.space-track.org'

print("[x] Logging into Space-Track...",end='')

# attempt to log into space track
space_parameters = {'identity': space_user ,' password': space_pass }
try:
    space_login = requests.post(spacebaseURL + '/ajaxauth/login', data=space_parameters)
except:
    print("Error cannot connect with web services.")
    sys.exit(1)

debug_respond_status(space_login.status_code)

print("[x] Retrieving TLE for sat [%s]...." % sat_id, end='')

# use cookie from login to retrieve tle
spaceURL = spacebaseURL + "/basicspacedata/query/class/tle_latest/ORDINAL/1--5/orderby/TLE_LINE1 ASC/format/3le/NORAD_CAT_ID/" + sat_id
try:
    tle = requests.get(spaceURL, cookies=space_login.cookies)
except:
    print("Error cannot connect with web services.")
    sys.exit(1)

# break tle into lines
tle_lines = tle.text.splitlines(True)

debug_respond_status(tle.status_code)

print("[x] Looking up location of zip [%s]...." % zipcode, end='')

# lookup zip code
zip_data = ZipcodeSearchEngine().by_zipcode(zipcode)

# ensure we found what we were looking for and not a 'best guess' or invalid zip
if (zip_data["Zipcode"] != zipcode):
    print("Invalid US Zipcode!")
    sys.exit(1)

print("OK!")

print("[x] Obtaining 16 day weather forecast....", end='')

# openweathermap login info
appId = 'dbaa716c704f2be156a160be3a8ff238'
parameter = 'zip='+zipcode+',us&cnt=16&appid=' + appId
owmurl = 'http://api.openweathermap.org/data/2.5/forecast/daily?' + parameter

cleardays = []
weather = []
try:
    resp = requests.get(owmurl)
except:
    print("Error cannot connect with web services.")
    sys.exit(1)

debug_respond_status(resp.status_code)
json_object = resp.json()

# Get clear days when cloudiness of the sky is less than 20%
for i in range(16):
    cloud = json_object["list"][i]["clouds"]
    time = json_object["list"][i]["dt"]
    readable_time = datetime.datetime.fromtimestamp(time).strftime('%Y-%m-%d')
    weather.append([readable_time, cloud])
    if cloud < 20:
        cleardays.append(readable_time)

print("[x] Calculating orbits....", end='')

# load tle and create observer at our zip location
iss = ephem.readtle(tle_lines[0], tle_lines[1], tle_lines[2])
obs = ephem.Observer()

obs.date = datetime.datetime.utcnow()

obs.lat = zip_data.Latitude
obs.lon = zip_data.Longitude
obs.horizon = '-0:34'

all_pass = []
e_data = []

# the following code was adapted from the slides
# by Mark VandeWettering and 'harry1795671' of stackexchange
for p in range(100):
    try:
        tr, azr, tt, altt, ts, azs = obs.next_pass(iss)
    except:
        print("Provided Sat doesn't seem to pass you, check id.")
        sys.exit(1)

    found = False
    current_pass = []

    # save one line from every 4th pass to condense printed data
    if p % 4 == 0:
        obs.date = tr
        iss.compute(obs)
        e_data.append([tr, math.degrees(iss.alt), math.degrees(iss.az)])

    while tr < ts :
        obs.date = tr

        sun = ephem.Sun()
        sun.compute(obs)
        iss.compute(obs)

        sun_alt = math.degrees(sun.alt)

        if iss.eclipsed is False and -18 < sun_alt < -6:
            current_pass.append(tr)
            found = True

        tr = ephem.Date(tr + ephem.second)
    if found is True:
        obs.date = current_pass[0]
        iss.compute(obs)
        sat_start_pos = [ iss.sublat, iss.sublong ]
        obs.date = current_pass[-1]
        iss.compute(obs)
        sat_end_pos = [ iss.sublat, iss.sublong ]
        sat_duration = current_pass[-1]-current_pass[0]
        sat_direction = [ sat_end_pos[0] - sat_start_pos[0], sat_end_pos[1] - sat_start_pos[1] ]
        all_pass.append({ "time":current_pass[0].datetime(), "pos":sat_start_pos, "direction":sat_direction, "duration":sat_duration })
    obs.date = tr + ephem.minute

print("OK!")

print("[x] Calculating weather permitting viewings....", end='')

viewable_event = []

for index in all_pass:
    pass_date = str(index['time']).split()[0].split('-')
    pass_month = int(pass_date[1])
    pass_day = int(pass_date[2])

    for cleardate in cleardays:
        clear_date = str(cleardate).split('-')
        clear_month = int(clear_date[1])
        clear_day = int(clear_date[2])
        if clear_month == pass_month and clear_day == pass_day:
            viewable_event.append(index)
print("Got %d!" % len(viewable_event))

print ("\nPass date and time without weather condition:")

for ind in all_pass:
    print (str(ind['time']).split())

print("\nTLE Data:")
print("",tle_lines[0],tle_lines[1],tle_lines[2])

print("Zipcode Location:")
print(zip_data.City)
print(" Lat = ", zip_data.Latitude)
print(" Long = ", zip_data.Longitude)

print("\n15 Day Forecast:")
for day in weather:
    print(" Date: ", day[0], " Cloud Coverage: ", day[1])

print("\nSample of satellite’s ephemeris data:")
for line in e_data:
    print("",line[0],line[1],line[2])

print()

num_events = len(viewable_event)

if num_events < 5:
    print("Weather conditions prohibit five viewable events on a 16-day forecast window.")
    if num_events == 0:
        print("There are no viewable events.")
        sys.exit(1)
    print("However, here are", num_events, "viewable events:")
else:
    print("The next 5 viewable events:")
    num_events = 5

print(" Date                       | Position               | Direction              | Duration")
print("----------------------------+------------------------+------------------------+---------")

for event in range(0,num_events):
    print(viewable_event[event]['time']," | (%+6f, %+6f) | (%+6f, %+6f) | "
          % (viewable_event[event]['pos'][0],viewable_event[event]['pos'][1], viewable_event[event]['direction'][0],
          viewable_event[event]['direction'][1]), viewable_event[event]['duration'])

##while datetime.datetime.now() + datetime.timedelta(minutes=15) < viewable_event[0]['time']:
##    pass
##
##try:
##    client.messages.create(to="+17036579073", from_="+17036915620",
##                               body="a satellite approacheth! (with in 15 minutes)")
##except:
##    print("Error: failed to send SMS text message")
##
### send sound
##try:
##    os.system('mpg123 -q example.mp3 &')
##except:
##    print("Error: sound failed to play")

##while datetime.datetime.now() < viewable_event[0]['time']:
##    pass
##    # flash LED
##    try:
##        GPIO.output(6, True)
##        sleepy.sleep(1.0)
##        GPIO.output(6, False)
##        sleepy.sleep(1.0)
##    except:
##        print("Error: failed to change GPIO output")

