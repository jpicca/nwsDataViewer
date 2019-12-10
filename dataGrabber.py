import requests
import pandas as pd
from pandas.io.json import json_normalize
from datetime import datetime

# Enter lat & lon
# At some point, I'd like to make a simple web app that can pass a 
# lat/lon to this script to update forecast location
lat = 32.8866
lon = -97.0423

apiEnd = 'https://api.weather.gov/points/' + str(lat) + ',' + str(lon)

# Send a request to the NWS API
request = requests.get(apiEnd)

# Get the json from the request
metaJson = request.json()

# Get responses for both the period forecasts, using the provided endpoint 
# from init response. Then grab the "clean" json
forecastRequest = requests.get(metaJson['properties']['forecast'])
forecastGridRequest = requests.get(metaJson['properties']['forecastGridData'])

forecast = forecastRequest.json()
forecastGrid = forecastGridRequest.json()

# Take json and convert to a dataframe
periodForecast = json_normalize(forecast['properties']['periods'])

# Due to the format of the grid forecast json, we have to break up the 
# forecast variables into their own dataframes
temps = json_normalize(forecastGrid['properties']['temperature']['values'])
pop = json_normalize(forecastGrid['properties']['probabilityOfPrecipitation']['values'])
sky = json_normalize(forecastGrid['properties']['skyCover']['values'])

# Format the validtime column so we can merge these dataframes
pop['validTime'] = pop['validTime'].str.split('/', n = 1, expand = True)[0].to_frame(name='validTime')
temps['validTime'] = temps['validTime'].str.split('/', n = 1, expand = True)[0].to_frame(name='validTime')
sky['validTime'] = sky['validTime'].str.split('/', n = 1, expand = True)[0].to_frame(name='validTime')

# Create an "hourlyWx" dataframe from the gridded variables
hourlyWx = temps.merge(pop,on='validTime',how='outer').merge(sky,on='validTime',how='outer')

# Get current UTC hour and format to match validTime entries of gridded wx df. Then find that hour in the df, 
# and use the index to find rows we want from the df (for the next 12 hours)
now = datetime.utcnow().strftime("%Y-%m-%dT%H:00:00+00:00")
currentHourIdx = hourlyWx[hourlyWx['validTime'] == now].index.tolist()[0]
next12hours = hourlyWx.loc[currentHourIdx:(currentHourIdx + 11)]

# Rename the columns and convert Celsius to Fahrenheit
next12hours = next12hours.rename(columns={'value_x':'TempF','value_y':'PoP','value':'SkyCover'})
next12hours['TempF'] = next12hours['TempF']*9/5 + 32