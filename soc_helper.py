#!/usr/bin/env python3

"""
soc_helper
Copyright (C) 2023-2024  M. Williges (spam at zut punkt de)

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

# System-Importe
import logging
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import json
import sys
import time
import importlib
import shutil
from os.path import exists
import os
import energylog
import txstack

# Importe von lokalen Dateien
import configuration	# Konfiguration des soc_helper.py
import spritmonitor	# Zum Prüfen bei Programmstart

# rudimentäre Prüfung der Konfiguration
def checkConfig():
    logging.debug('Prüfe Konfiguration...')
    # Prüfen ("-": noch nicht vorhanden, "+": vorhanden):
    # ( -Ob die Wallbox unter der angegebenen IP ereichbar ist
    #   -Ob die Fahrzeuge mit den IDs auch in der Wallbox vorhanden sind) - Noch keine Verbindung zum MQTT-Server zu
    #   diesem Zeitpunkt
    # +Ob lokale Logdatei schreibbar ist, wird in energylog.py geprüft
    # +Ob hinreichend freier Plattenspeicher vorhanden ist für das Log
    # +Ob die Namen der Fahrzeuge eindeutig sind (keine Doubletten)
    # +Ob die OpenWB-IDs eindeutig sind
    # +Ob eine IP-Adresse für die Wallbox-Steuerung angegeben ist
    # +Ob bei Spritmonitor ein Kilometerstand abrufbar ist, sofern Spritmonitor genutzt werden soll:
    # +Wenn SPEAKS_UDS == True ist, muss SOC_REQ_ID gesetzt und ungleich 0 sein
    # +Wenn SPEAKS_UDS == True ist, muss ODO_REQ_ID gesetzt sein, sofern Spritmonitor genutzt werden soll!

    # Genug Plattenplatz vorhanden (mindestens 5MB?)
    fs = shutil.disk_usage('.').free
    logging.debug(f'Freier Speicher: {fs/1024/1024} MB.')
    if fs < 1024*1024*5:
        logging.warn('Achtung: Weniger als 5MB Speicher vorhanden.')
    
    # IP-Adresse der OpenWB vorhanden?
    logging.debug('Prüfe auf OpenWB-IP-Adresse')
    if not hasattr(configuration, 'OPENWB_IP'):
        logging.error('OPENWB_IP ist undefiniert')
        sys.exit()

    # IP-Adresse der OpenWB funktionsfähig?

    # Doppelte Namen?
    logging.debug('Prüfe auf eindeutige Fahrzeugnamen')
    seen = set()
    dupes = []
    for car in configuration.myCars:
        if car.name in seen:
            dupes.append(car.name)
        else:
            seen.add(car.name)
    if len(dupes) > 0:
        logging.error(f'Fahrzeugnamen müssen eindeutig sein. Fahrzeuge mit doppeltem Namen: {dupes}')
        sys.exit()
    # Doppelte IDs?        
    logging.debug('Prüfe Fahrzeuge auf eindeutige OpenWB-IDs')
    seen = set()
    dupes = []
    for car in configuration.myCars:
        if car.openwbVehicleId in seen:
            dupes.append(car.openwbVehicleId)
        else:
            seen.add(car.openwbVehicleId)
    if len(dupes) > 0:
        logging.error(f'Fahrzeug-IDs müssen eindeutig sein. Mehrfach vorhandene IDs: {dupes}')
        sys.exit()
    # Kilometerstand bei Spritmonitor erreichbar?
    logging.debug('Prüfe Abrufbarkeit der letzten Kilometerstände bei Spritmonitor')
    bearer = False	# Bearer Token nur einmal prüfen, wenn überhaupt
    for car in configuration.myCars:
        logging.debug(f'{car.name}: Spritmonitor benutzen? {car.useSpritmonitor}')
        if car.useSpritmonitor is True:
            # Prüfen, ob bei Spritmonitor-Nutzung ein BEARER-Token gesetzt ist
            if not bearer:
                bearer_token = os.environ.get("SPRITMONITOR_BEARER_TOKEN")
                if bearer_token == None:
                    logging.error('Spritmonitor aktiv gesetzt, aber Umgebungsvariable SPRITMONITOR_BEARER_TOKEN nicht gesetzt, siehe Dokumentation.')
                    sys.exit()
                else:
                    bearer = True
            # Bearer-Token vorhanden
            lastFueling = spritmonitor.get_last_fuel_entry(car.spritmonitorVehicleId)
            logging.debug('Antwort von Spritmonitor auf probeweises Abrufen des letzten Kilometerstandes: %s',lastFueling)
            if isinstance(lastFueling, list):
                if len(lastFueling) > 0:
                    td = json.loads(json.dumps(lastFueling[0]))
                    if 'odometer' in td:
                        logging.debug(f'Letzter Spritmonitor-Kilometerstand von Fahrzeug {car.name} erfolgreich abgerufen: {td}.')
                    else:
                        # should not happen ;-)
                        logging.error(f'Letzter Spritmonitor-Kilometerstand ergibt Liste mit mindestens einem Eintrag, aber ohne "odometer"')
                        sys.exit()
                else:
                    logging.warning(f'Kein letzter Spritmonitor-Kilometerstand für Fahrzeug {car.name}. Nächster Ladvorgang wird Erstbeladung.')
            else:
                logging.error(f'Probeweises Auslesen des letzten Kilometerstandes bei Spritmonitor ergibt keine Liste {lastFueling}. Passen Bearer-Token und Fahrzeunummer?')
                sys.exit()

    # Für SPEAKS_UDS == True muss SOC_REQ_ID gesetzt und >0 sein
    logging.debug('Prüfe, ob SOC_REQ_ID gesetzt und >0 ist')
    for car in configuration.myCars:
        if car.SPEAKS_UDS:
            if hasattr(car, 'SOC_REQ_ID'):
                if car.SOC_REQ_ID > 0:
                    logging.debug(f'{car.name}: Spricht UDS. SOC_REQ_ID ist gesetzt. OK.')
                    # Für SPEAKS_UDS == True muss ODO_REQ_ID gesetzt und >0 sein, sofern Spritmonitor aktiv ist.
                    if car.useSpritmonitor is True:
                        if hasattr(car, 'ODO_REQ_ID'):
                            if car.ODO_REQ_ID == 0:
                                logging.error(f'{car.name} spricht UDS und nutzt Spritmonitor, ODO_REQ_ID ist aber 0. cars.py ist fehlerhaft.')
                                sys.exit()
                        else:
                            logging.error(f'{car.name} spricht UDS und nutzt Spritmonitor, hat aber kein ODO_REQ_ID gesetzt. cars.py ist fehlerhaft.')
                            sys.exit()
                else:
                    logging.error(f'{car.name} spricht UDS, hat aber SOC_REQ_ID ist 0. cars.py ist fehlerhaft.')
                    sys.exit()
            else:
                logging.error(f'{car.name} spricht UDS, aber SOC_REQ_ID ist nicht gesetzt. cars.py ist fehlerhaft.')
                sys.exit()
#
# Callback-Funktionen
#

# Erfolgreicher Verbindung zur OpenWB (CONNACK)
def on_connect(client, userdata, flags, rc):
    logging.info(f'Verbindung hergestellt zu {configuration.OPENWB_IP} mit Resultat {rc}')
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe('#')

def on_disconnect(client, userdata, rc):
    logging.info(f'Verbindung zu {configuration.OPENWB_IP} gelöst.')

#
# Hauptprogramm
#

# Logger anlegen
FORMAT = "%(asctime)s;%(levelname)9s;[%(filename)19s:%(lineno)3s - %(funcName)16s() ] %(message)s"
logging.basicConfig(encoding='utf-8', format=FORMAT, level=logging.getLevelName(configuration.LOGLEVEL))
logging.critical('Starte soc_helper Version 2025-04-22')

# Prüfen der Konfiguration
checkConfig()

# Anlegen / Öffnen der lokalen Ladelogdatei
energylog.init(configuration.CHARGELOG_PATH)

# MQTT-Client einrichten und mit dem Broker verbinden
client = mqtt.Client()
client.on_pre_connect = None
client.on_connect = on_connect
client.on_subscribe = None
client.on_disconnect = on_disconnect

try:
    # MQTT-Topic-Abos einrichten und mit Callback-Funktionen verbinden
    logging.info(f'Verbinde Callbackfunktionen der Ladepunkte:')
    for cp in configuration.myChargepoints:
        logging.info(f'Ladepunkt {cp.chargepointId}')
        m = cp.getCounterTopic()
        logging.debug(f'Abonniere {m}')
        client.message_callback_add(m, cp.cb_energycounter)		# Zählerstand von Chargepoint cp empfangen
        m = cp.getConnectedIdTopic()
        logging.debug(f'Abonniere {m}')
        client.message_callback_add(m, cp.cb_connectedVehicle)	# ID des im Ladepunkt eingestellten Fahrzeugs empfangen
        m = cp.getPlugStateTopic()
        logging.debug(f'Abonniere {m}')
        client.message_callback_add(m, cp.cb_plug)			    # Ladesteckerzustand von Chargepoint cp empfangen
    logging.info(f'Verbinde Callbackfunktionen der Fahrzeuge:')
    for car in configuration.myCars:
        logging.info(f'Fahrzeug {car.name}')
        m = car.getStatusTopic()
        logging.debug(f'Abonniere {m}')
        client.message_callback_add(m, car.cb_status)		# WiCAN-Statusbotschaft empfangen für car
        m = car.getRxTopic()
        logging.debug(f'Abonniere {m}')
        client.message_callback_add(m, car.cb_rx)			# WiCAN-Botschaft empfangen für car
        m = car.getgetSocTopic()
        logging.debug(f'Abonniere {m}')
        client.message_callback_add(m, car.cb_getOpenwbSoc)		# Berechneter SoC aus der Wallboc für car
except Exception as e:
    logging.error(f'FATAL: Fehler beim Abonnieren beim Broker auf {configuration.OPENWB_IP}: {e}')
    quit()

# Verbindung zum MQTT-Broker in der Wallbox herstellen
logging.debug(f'Verbindungsversuch mit MQTT-Broker der Wallbox unter Adresse {configuration.OPENWB_IP}.')
try:
    client.connect(configuration.OPENWB_IP, 1883, 60)
except Exception as e:
    logging.error(f'FATAL: Fehler beim Versuch, Verbindung mit Broker {configuration.OPENWB_IP} herzustellen: {e}')
    quit()
client.loop_start()

try:
    while True:
        txstack.tx(client)
        time.sleep(0.5)
except KeyboardInterrupt:
    logging.error('Abbruch durch Benutzer')
except Exception as e:
    logging.error(f'Exception in der Endlosschleife: {e}')

client.loop_stop()
