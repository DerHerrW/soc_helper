"""
Interface to Spritmonitor. Used functions are mostly copied from Spritmonitor Github Repo at
https://github.com/FundF/Spritmonitor-API-sample-code/tree/main

Copyright 2023 Martin Williges

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import requests
import os
SM_API_URL = "https://api.spritmonitor.de/v1"

# To set your enviornment variables in your terminal run the following line:
# export 'BEARER_TOKEN'='<your_bearer_token>'
bearer_token = os.environ.get("SPRITMONITOR_BEARER_TOKEN")
app_token = '4a5379db9f8530b11096ff4c917bdc9a'

def bearer_auth(r):
    """
    Set authorization header
    """

    r.headers["Authorization"] = f"Bearer {bearer_token}"
    r.headers["Application-ID"] = app_token
    r.headers["User-Agent"] = "soc_helper"
    return r

def connect_to_sm_rest(url):
    """
    Send request to Spritmonitor REST endpoint
    """
    respose = requests.request("GET", url, auth=bearer_auth)
    if respose.status_code != 200:
        raise Exception(
            "Request returned an error: {} {}".format(
                respose.status_code, respose.text
            )
        )
    return respose.json()

def get_last_fuel_entry(vehicle_id):
    """
    Retrieve fuel entries from vehicle with given id
    """

    if vehicle_id == 0:
        raise Exception("Invalid vehicle ID")

    url = f"{SM_API_URL}/vehicle/{vehicle_id}/fuelings.json?limit=1"
    entries = connect_to_sm_rest(url)
    return entries

def add_fuel_entry(vehicle, tank, date, type, odometer, trip, quantity, quantityunit, fuelsort, priceperkwh, soc, attributes):
    """
    vehicle         Numeric Spritmonitor ID of vehicle to add a fuel up
    tank            Numeric ID of tank of vehicle to add a fuel up
    date            Date of fuel up in format DD.MM.YYYY
    type            Type of fuel up, must be one of: full, notfull, first, invalid
    odometer        Odometer value of fuel up
    trip            Driven distance since last fuel up
    quantity        Amount of fuel filled up
    quantityunit    Numeric ID of quantity unit, e.g. 1 for liter, 2 for US gallon, etc. For full list see general infos sample code
    fuelsort        Fuel sort of fuel up, e.g., 1 for diesel, 6 for gasoline, etc. For full list see general infos sample code
    price           Total cost of fuel up
    currency        Numeric ID of currency, e.g., 0 for EUR, 2 for USD, etc. For full list see general infos sample code
    attributes      Combination of one tire type (wintertires,summertires,allyeartires) and one driving style (slow,normal,fast) and one or more extras (ac,heating,trailer)
    streets         Combination of city, autobahn, land
    percent         Only for electric vehicles: Specifies the charge level in percent _after_ charging, only applicable for notfull charges
    charge_power    Only for electric vehicles: Specifies the power level in kW that was used to charge the vehicle
    charge_duration Only for electric vehicles: Specifies the duration in minutes that the vehicle was charged
    charge_info     Only for electric vehicles: Specifies the current type (ac,dc) as well as the source of measurement (source_wallbox,source_vehicle)
    """
    if vehicle == 0:
        raise Exception("Invalid vehicle ID")

    url = (f"{SM_API_URL}/vehicle/{vehicle}/tank/{tank}/fueling.json?date={date}&type={type}&odometer={odometer}&price={priceperkwh}&pricetype=1" 
           f"&currencyid=0&trip={trip}&quantity={quantity}&quantityunitid={quantityunit}&fuelsortid={fuelsort}&stationname={'daheim'}"
           f"&note={'automatisch übertragen von soc_helper.py'}&percent={soc}&attributes={attributes}&charging_power=11&charge_info={'ac,source_wallbox'}")
    result = connect_to_sm_rest(url)
    return(result)
     
