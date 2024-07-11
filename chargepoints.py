"""
chargepoints.py
Stellt die für Ladepunkte notwendigen Daten und Methoden zur Verfügung.
"""

from dataclasses import dataclass
import logging
import json
import datetime
import cars
import spritmonitor
import configuration
import energylog

@dataclass
class chargepoint:
    # Variablen
    chargepointId: int = 1	    # Default-Nummer des Ladepunktes
    plugstate: bool = False	    # Zustand Ladestecker
    counterAtPlugin: float = None   # Zählerstand beim Stecken des Stecker
    counter: float = None	    # zuletzt übermittelter Zählerstand
    connectecId: int = None         # aktuell im Ladepunkt eingestelltes Fahrzeug    
    
    # Hilfsfunktionen
    def getCounterTopic(self):
        return('openWB/chargepoint/'+str(self.chargepointId)+'/get/imported')
    def getPlugStateTopic(self):
        return('openWB/chargepoint/'+str(self.chargepointId)+'/get/plug_state')
    def getConnectedIdTopic(self):
        return('openWB/chargepoint/'+str(self.chargepointId)+'/get/connected_vehicle/info')
        
    # Callback-Methoden
    def cb_energycounter(self, client, userdata, msg):
        # Gesamtzählerstand
        self.counter = float(msg.payload)
        logging.debug(f'Zählerstand auf Ladepunkt {self.chargepointId}: {self.counter}')
        
    def cb_connectedVehicle(self, client, userdata, msg):
        # ID des eingestellten Fahrzeugs
        # Überdenken: Diverse Daten werden bei Einbuchen ins WLAN übertragen, bevor man die Möglichkeit hat,
        # das Fahrzeug an der Wallbox ggf richtig einzustellen. Daher sollte connectedId nur ausgewertet werden,
        # wenn der Stecker gezogen wird.
        self.connectedId = json.loads(msg.payload)['id']
        logging.debug(f'ID des mit Ladepunkt {self.chargepointId} verbundenes Fahrzeugs: {self.connectedId}')
        
    def cb_plug(self, client, userdata, msg):
        # Stecker des Ladepunktes
        logging.debug(f'Steckerzustand von Ladepunkt {self.chargepointId}: {msg.payload}')
        if (b'true' in msg.payload) or (b'1' in msg.payload):
            if not self.plugstate:
                # Wechsel von 0 auf 1 (Anstecken)
                self.plugstate = True
                self.counterAtPlugin = self.counter
        else:
            if self.plugstate:
                # Wechsel von 1 auf 0 (Abstecken)
                self.plugstate = False
                # Auf kWh umrechnen und mit 3 Nachkommastellen runden
                if self.counter is not None and self.counterAtPlugin is not None:
                    lastCharged = round( (self.counter - self.counterAtPlugin)/1000, 3)
                else:
                    logging.warn(f'Aktueller Stromzählerstand oder Zählerstand beim Anstecken war undefiniert.')
                    lastCharged = 0;
                logging.info(f'Stecker von Ladepunkt {self.chargepointId} gezogen. Lademenge {lastCharged} geladen in Fahrzeug {self.connectedId}.')
                # Fahrzeugindex herausfinden
                found = False
                for car in configuration.myCars:
                    if car.openwbVehicleId == self.connectedId:
                        logging.debug(f'Abgestecktes Fahrzeug mit openwbId {self.connectedId} als {car.name} in der Fahrzeugliste identifiziert')
                        found = True
                        break
                if not found:
                    logging.warn(f'in der Wallbox eingestelltes Fahrzeug mit ID {self.connectedId} ist nicht in der Fahrzeugliste aufgeführt')
                # Zeitpunkt des Endes des Ladevorganges
                datetimeAtPlugOut = datetime.datetime.now() 	# Datum des Ladeendes
                date = datetimeAtPlugOut.strftime('%d.%m.%Y')   # Datum in lesbarer Form für lokale Datei und ggf. Spritmonitor
                # lokales Abspeichern
                if found:
                    #Fahrzeug in Liste gefunden
                    energylog.write(date+', '+car.name+', '+str(car.odo)+', '+str(lastCharged)+', '+str(car.soc)+', '+str(car.openwbsoc)+'\n')
                    #Spritmonitor-Teil nach Ladeabschluß
                    if car.useSpritmonitor and (lastCharged >= 0.1):
                        logging.debug(f'Spritmonitor ist konfiguriert. Beginne Übermittlung.')
                        # letzten bei Spritmonitor eingetragenen km-Stand auslesen
                        lastFueling = spritmonitor.get_last_fuel_entry(car.spritmonitorVehicleId)
                        if len(lastFueling) > 0:
                            td = json.loads(json.dumps(lastFueling[0]))
                            lastOdo = float(td['odometer'])
                            logging.debug(f'Letzter Spritmonitor-Kilometerstand ist {lastOdo}.')
                        else:
                            lastOdo = 0.0
                            logging.warning(f'Konnte keinen letzter Spritmonitor-Kilometerstand ermitteln, nehme 0 an.')
                        logging.info(f'Ladung wurde mit berechneten {car.openwbsoc}% beendet.')
                        # type-Variable für Füllung bestimmen
                        if lastOdo == 0.0:
                            fuel_type = "first"
                        elif ( abs(float(car.openwbsoc)-100)<=2.0 ):
                            fuel_type = "full" 
                        else:
                            fuel_type = "notfull"
                        trip = round(car.odo - lastOdo,2)
                        if trip < 0.1:
                            trip = 0.0
                        logging.info(f'Letzter Spritmonitor-Kilometerstand: {lastOdo}; aktueller Kilometerstand: {car.odo} trip: {trip}')
                        quantityunitid = 5 # 'kWh'
                        # "Betankung" übermitteln
                        result=spritmonitor.add_fuel_entry(car.spritmonitorVehicleId, 1,date, fuel_type, car.odo, trip, lastCharged,
                                quantityunitid, car.spritmonitorFuelsort, car.spritmonitorFuelprice,car.openwbsoc,car.spritmonitorAttributes)
                        logging.debug(f'Ergebnis der Übermittlung: {result}')
                        logging.info(f'Übermittlung an Spritmonitor ist erfolgt.')
                else:
                    # undefiniertes Fahrzeug angesteckt
                    energylog.write(date+', undefiniertes Fahrzeug, -,'+str(lastCharged)+', -, -\n')
