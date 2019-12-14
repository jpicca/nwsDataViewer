import requests
import pandas as pd
from pandas.io.json import json_normalize
import datetime

# Enter lat & lon
# At some point, I'd like to make a simple web app that can pass a 
# lat/lon to this script to update forecast location
lat = 32.8866
lon = -97.0423

apiEnd = 'https://api.weather.gov/points/' + str(lat) + ',' + str(lon)

# Try sending a request to the NWS API. If an error (connection, http, etc.) is raised, shut it down.
try:
    request = requests.get(apiEnd)
except requests.exceptions.RequestException as e: 
    print(e)
    sys.exit(1)

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

# Convert the validTime columns to actual useable datetime values
pop['validTime'] = pd.to_datetime(pop['validTime'],format="%Y-%m-%dT%H:00:00+00:00")
temps['validTime'] = pd.to_datetime(temps['validTime'],format="%Y-%m-%dT%H:00:00+00:00")
sky['validTime'] = pd.to_datetime(sky['validTime'],format="%Y-%m-%dT%H:00:00+00:00")

# Create a list that will include +/-24 hours of times from current time -- use to make dataframe
# Go back 24 hours to ensure we grab first data point from NWS API
nextHour = datetime.datetime.utcnow().replace(microsecond=0,second=0,minute=0)-datetime.timedelta(hours=24)

timeList = []

for i in range(49):
    timeList.append(nextHour + datetime.timedelta(hours=i))

# Generate dataframe to merge with pop/temps/sky
weatherData = pd.DataFrame(timeList, columns=['validTime'])

# Merge pop/temps/sky, using how=left --> we use only keys from the calling dataframe
weatherData = weatherData.merge(pop,on='validTime', how='left').merge(temps,on='validTime', how='left') \
                .merge(sky,on='validTime', how='left')

# Replace NaNs with last available data (NWS API may skip some hours... so we need to fill those spots)
weatherData = weatherData.fillna(method='ffill')

# Get index of the present time and take a slice of our dataframe for just the hours we want
now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:00:00")
currentHourIdx = weatherData[weatherData['validTime'] == now].index.tolist()[0]
weatherData = weatherData.loc[currentHourIdx:(currentHourIdx + 23)]

# Correct celsius to fahrenheit and rename columns
weatherData['value_y'] = weatherData['value_y']*9/5+32
weatherData = weatherData.rename(columns={'value_x':'pop', 'value_y':'tempF', 'value':'sky'})

weatherData.to_csv('./next24hours.csv')

'''
# Create an "hourlyWx" dataframe from the gridded variables & replace NaNs with most recent value
hourlyWx = temps.merge(pop,on='validTime',how='outer').merge(sky,on='validTime',how='outer')
hourlyWx = hourlyWx.fillna(method='ffill')

# Create a column that keeps track of the time change between this row and the next
# We need to be aware if it skips more than 1 hour (we'll have to handle the gap)
hourlyWx['hourDelta'] = (pd.to_datetime(hourlyWx['validTime'].shift(-1)) - pd.to_datetime(hourlyWx['validTime'])).dt.seconds/3600


# Get current UTC hour and format to match validTime entries of gridded wx df. Then find that hour in the df, 
# and use the index to find rows we want from the df (for the next 12 hours)
now = datetime.utcnow().strftime("%Y-%m-%dT%H:00:00+00:00")
currentHourIdx = hourlyWx[hourlyWx['validTime'] == now].index.tolist()[0]
next24hours = hourlyWx.loc[currentHourIdx:(currentHourIdx + 23)]

# Rename the columns and convert Celsius to Fahrenheit
next24hours = next24hours.rename(columns={'value_x':'TempF','value_y':'PoP','value':'SkyCover'})
next24hours['TempF'] = next24hours['TempF']*9/5 + 32

next24hours.to_csv('./next24hours.csv')
'''