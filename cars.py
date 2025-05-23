"""
cars.py
Definiert die OBD2-Kommandos der zur Auswahl stehenden Fahrzeuge und baut aus den Angaben in configuration.py mit den OBD2-Kommandos
für jeden Fahrzeugtyp eine Fahrzeugklasse zusammen.

part of project soc_helper
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

from dataclasses import dataclass, field
from typing import List
import logging
import json
import urllib.request
import txstack
from Sun import Sun

validCars = ("eUp", "eGolf", "VwMEB", "Fiat500e", "OraFunkyCat", "ZoePH1", "StandardFuelLevel")

@dataclass
class carclass:
    # Vorlage für die Nutzerdaten aller Fahrzeugklassen.
    name: str = 'UnnamedCar'
    openwbVehicleId: int = 1
    useSpritmonitor: bool = False
    spritmonitorVehicleId: int = 0
    spritmonitorFuelsort: int = 19
    spritmonitorFuelprice: float = 0.27
    spritmonitorAttributes: str = 'wintertires, slow'
    actionURL: str = ''
    odo: float = 0		# Letzter vom Fahrzeug empfangener Kilometerstand
    soc: float = 0		# Letzter vom Fahrzeug emfangener SoC
    socAtPlugin: float = 0	# Inhalt von soc im Moment des Einsteckens des Ladesteckers
    openwbsoc: float = 0        # Letzter von der Wallbox empfangener (berechneter) SoC
    
    # Hilfsfunktionen
    def getStatusTopic(self):
        return('others/wican/'+self.name+'/status/#')
    def getRxTopic(self):
        return('others/wican/'+self.name+'/can/rx/#')
    def getTxTopic(self):
        return('others/wican/'+self.name+'/can/tx')
    def getgetSocTopic(self):
        return('openWB/vehicle/'+str(self.openwbVehicleId)+'/get/soc')
    def getsetSocTopic(self):
        return('openWB/set/vehicle/'+str(self.openwbVehicleId)+'/soc_module/calculated_soc_state/manual_soc')
        
    # Callback-Funktionen
    def cb_status(self, client, userdata, msg):
        # Die Funktion wird beim Start verbunden mit dem jeweiligen Statustopic des WiCAN,
        # der zu dem Fahrzeug gehört.
        logging.debug(f'cb_status von Fahrzeug {self.name} aufgerufen')
        logging.info(f'WiCAN-Status: {msg.topic} {msg.payload}')
        # Statusbotschaft empfangen. Prüfen, ob online
        try:
            s=json.loads(msg.payload)
            if s['status'] == 'online':
                # Wenn das Fahrzeug online geht, kann der SOC und der Gesamtkm-Stand abgefragt werden
                if self.SPEAKS_UDS is True:
                    logging.info(f'Fahrzeug {self.name} ist online. Sende SOC- und ODO-Anforderung')
    
                    if self.SOC_REQ_ID == 0:
                        logging.info(f'SOC_REQ_ID ist 0, sende keine Anforderung')
                    else:
                        logging.debug(f'Stelle SOC-Anforderung in Anfrageliste: {self.SOC_REQUEST}')
                        txstack.add2stack(self.getTxTopic(),self.SOC_REQUEST)
    
                    if self.ODO_REQ_ID == 0:
                        logging.info(f'ODO_REQ_ID ist 0, sende keine Anforderung')
                    else:
                        logging.debug(f'Stelle ODO-Anforderung in Anfrageliste: {self.ODO_REQUEST}')
                        txstack.add2stack(self.getTxTopic(),self.ODO_REQUEST)

                else:
                    logging.info(f'Fahrzeug {self.name} ist online, spricht aber kein UDS. Keine Aktion.')
            else:
                logging.info(f'Fahrzeug {self.name} ist <<offline>>')
        except Exception as e:
            logging.warning(f'Fehler beim Parsen der Statusnachricht: {e}')
        
    def cb_getOpenwbSoc(self, client, userdata, msg):
        logging.debug(f'cb_getOpenwbSoc von Fahrzeug {self.name} aufgerufen')
        try:
            self.openwbsoc = float(msg.payload)
        except Exception as e:
            logging.warning(f'Fahrzeug {self.name}: Konnte von der Wallbox empfangenen SoC nicht in Zahl umwandeln: {e}')
            self.openwbsoc = 0
        logging.debug(f'Von der Wallbox für Fahrzeug {self.name} empfangener SoC: {self.openwbsoc}')
        return()
        
    def cb_rx(self, client, userdata, msg):
        # Callback-Funktion für eine CAN-Rx-Botschaft. Prüft, ob es eine SOC- oder ODO-haltige Botschaft ist
        # und sendet im Fall eines SOC den Wert zur OpenWB. Mehrteilige Botschaften werden aneinander gehängt.
        logging.debug(f'cb_rx von Fahrzeug {self.name} aufgerufen')
        logging.debug(f'Empfangene CAN-Botschaft: {msg.payload}')
        
        # In einer Botschaft können mehrere Frames zusammen kommen - momentan noch unklar, was bei Fortsetzungs-Frames inmitten
        # anderer Frames passiert
        try:
            frames = json.loads(msg.payload)['frame']
            logging.debug(f'Gesamte Frames: {frames}')
            # json.loads(msg.payload): String der Nutzlast als dict
            # json.loads(msg.payload)['frame']: Datenframe in f ergibt eine Liste mit einem Element
            # json.loads(msg.payload)['frame'][0]: Das nullte und einzige Element der Liste ist ein dict
        except Exception as e:
            logging.error(f'Fehler beim json-Parsen der empfangenen CAN-Botschaft: {e}')
            return
        if len(frames) == 0:
            loggin.error(f'Fehler: Empfangene Botschaft enthält keine Frames: {frames}')
            return
        
        if self.SPEAKS_UDS is True:
            # Fahrzeug sprich UDS - Fragen und Antworten nötig
            for f in frames:
                logging.debug(f'Frame: {f}')
                id = f['id']        # json.loads(msg.payload)['frame'][0]['id']: Sender-ID
                data = f['data']    # json.loads(msg.payload)['frame'][0]['data']: Liste der Nutzbytes vom CAN
                # Prüfe, ob die Botschaft mehrteilig oder einteilig ist
                tpType =  data[0] // 16        # Oberen Nibble von Byte 0 extrahieren
                self.messageComplete = False
                if tpType == 1:
                    # Erster Teil einer mehrteiligen Botschaft
                    # Anzahl zu empfangenen Bytes: 12 Bit aus unterem Nibble Byte 0 und ganzes Byte 1
                    self.bytesToReceive = (data[0] & 15)*256 + data[1]
                    self.payload = [id]
                    self.payload.extend(data[2:8])
                    self.bytesReceived = 6
                    logging.debug(f'Ersten Teil einer mehrteiligen Botschaft empfangen: {self.payload}')
                    # zu Sende-ID des Senders die passende Empfänger-ID suchen:
                    if id > 2047:	# FIXME: reicht das, oder muss ich die Information extd explizit in den abgeleiteten Klassen definieren?
                        ext = 'true'
                    else:
                        ext = 'false'
                    flowCtrl = None
                    if id == self.ODO_RESP_ID:
                        flowCtrl = '{ "bus": "0", "type": "tx", "frame": [{ "id": '+str(self.ODO_REQ_ID)+', "dlc": 8, "rtr": false, "extd": '+ext+', "data": [48,0,100,170,170,170,170,170] }] }'
                    elif id == self.SOC_RESP_ID:
                        flowCtrl = '{ "bus": "0", "type": "tx", "frame": [{ "id": '+str(self.SOC_REQ_ID)+', "dlc": 8, "rtr": false, "extd": '+ext+', "data": [48,0,100,170,170,170,170,170] }] }'
                    if flowCtrl is not None:
                        # Fordere alle weitere Botschaften an mit 100ms Pause zwischen den Frames
                        logging.debug(f'Aufforderung für Folgeteile absetzen: {flowCtrl}')
                        client.publish(self.getTxTopic(), flowCtrl)
                elif tpType == 2:
                    # Botschaft ist ein Folgeteil einer mehrteiligen Botschaft. Der Index sollte im unteren Nibble von Byte 0 stehen
                    # hier wird einfach gehofft, daß die Botschaften in der richtigen Reihenfolge ankommen. Sie werden stumpf angehängt.
                    if hasattr(self, 'payload') and hasattr(self, 'bytesToReceive'):
                        if self.bytesToReceive > 0:
                            self.payload.extend(data[1:8])     # Je Nachfolger sollten 7 Nutzbytes kommen
                            self.bytesReceived += 7
                            if self.bytesReceived >= self.bytesToReceive:
                                self.messageComplete = True
                                self.bytesToReceive = 0
                            logging.debug(f'Mehrteilige Botschaft komplett: {self.payload}')
                        else:
                            logging.debug(f'Unerwarteten Folgeteil einer mehrteiligen Botschaft empfangen: {self.payload} - verwerfe.')
                elif tpType == 0:
                    # Einteilige Botschaft
                    self.payload = [id]
                    self.payload.extend(data[1:8])
                    self.bytesReceived = 7
                    self.messageComplete = True
                    logging.debug(f'Einteilige Botschaft: {self.payload}')
                else:
                    logging.warning('Botschaft mit unbekanntem CAN-TP-Botschaftstyp oder FlowControl empfangen.')

                if self.messageComplete:
                    #in payload liegt eine Liste der komplett empfangenen Botschaft vor
                    # Erwartungswerte zusammenbauen (Kommando wird wiederholt)
                    lenSOC = self.SOC_REQ_DATA[0]
                    expectSOC = self.SOC_REQ_DATA[1:1+lenSOC]
                    expectSOC[0] += 64
                    logging.debug(f'Erwarteter SOC_Header: lenSOC: {lenSOC}; expectSOC: {expectSOC}')
                    lenODO = self.ODO_REQ_DATA[0]
                    expectODO = self.ODO_REQ_DATA[1:1+lenODO]
                    expectODO[0] += 64
                    logging.debug(f'Erwarteter ODO-Header: lenODO: {lenODO}; expectODO: {expectODO}')
                    if self.payload[0] == self.SOC_RESP_ID and self.payload[1:1+lenSOC] == expectSOC:
                        # Erwartungswert für SoC-Auslesekommando ist vorhanden, daher Konvertierung aufrufen
                        oldSoc = self.soc
                        logging.info(f'Empfangene SoC-Botschaft ist {self.payload}')
                        self.calcSOC(self.payload)
                        if self.soc is None:
                            logging.warning("Erhaltener SOC ist ungültig (Return-Wert None). Wird ignoriert")
                        elif self.soc<0 or self.soc>100:
                            logging.warning(f'Erhaltener SOC {self.soc} ist ungültig. Wird ignoriert.')
                        else:
                            logging.info(f'Fahrzeug-SOC ist {self.soc}')
                            logging.debug(f'SOC-Wert von {self.soc} an {self.getsetSocTopic()} schicken.')
                            try:
                                client.publish(self.getsetSocTopic(), self.soc)     #SOC-Wert an die OpenWB schicken.
                                if self.actionURL != '' and self.soc < (oldSoc-2):
                                    # es gibt einen shelly, der angesteuert werden soll und
                                    # neuer SoC ist hinreichend kleiner als der alte SoC vom
                                    # Losfahren -> Zeichen, daß Fahrzeug gefahren wurde
                                    # Funktioniert u.U. nicht, wenn extern gelöaden wurde!
                                    logging.info(f'Rufe Licht-URL {self.actionURL} auf')
                                    with urllib.request.urlopen(self.actionURL) as response:
                                        status = response.read()
                                        logging.debug(f'Antwort ist {status}')
                            except Exception as e:
                                logging.error(f'Schreiben des SOC an die Wallbox ist fehlgeschlagen: {e}')
                    elif self.payload[0] == self.ODO_RESP_ID:
                        # Erwartungswerte zusammenbauen
                        if self.payload[1:1+lenODO] == expectODO:
                            # Erwartungswert für Auslesekommando ist vorhanden, daher Konvertierung aufrufen
                            logging.info(f'Empfangene ODO-Botschaft ist {self.payload}')
                            self.calcODO(self.payload)
                            logging.info(f'Fahrzeug-Kilometerstand ist {self.odo}')
                            if self.odo == -1:  # Wert für "nicht bereit"
                                # Kilometerstand lieferte nur Einsen (meist bedeutet das "nicht bereit")
                                logging.warn('Kilometerstand nicht nutzbar. Sende erneute ODO-Anfrage')
                                client.publish(self.getTxTopic(), self.ODO_REQUEST)
                    else:
                        logging.warning(f'Empfangene Botschaft: {self.payload} ist keine gültige Antwort auf eine konfigurierte Anfrage')

                    # Botschaftsempfang zurücksetzen
                    self.messageComplete = False
        else:
            # Fahrzeug spricht kein UDS (ZoePH1 et al)
            for f in frames:
                id = f['id']        # json.loads(msg.payload)['frame'][0]['id']: Sender-ID
                data = f['data']    # json.loads(msg.payload)['frame'][0]['data']: Liste der Nutzbytes vom CAN
                self.payload = [id]
                self.payload.extend(data[0:8])
                logging.debug(f'Rohe CAN-Botschaft: {self.payload}')
                if self.payload[0] == self.SOC_RESP_ID:
                    oldSoc = self.soc
                    self.calcSOC(self.payload)
                    if self.soc is None:
                        logging.warning("Erhaltener SOC ist ungültig (Return-Wert None). Wird ignoriert")
                    elif self.soc<0 or self.soc>100:
                        logging.warning(f'Erhaltener SOC {self.soc} ist ungültig. Wird ignoriert.')
                    else:
                        logging.debug(f'Fahrzeug-SOC von {self.soc} an {self.getsetSocTopic()} schicken.')
                        try:
                            client.publish(self.getsetSocTopic(), self.soc)     #SOC-Wert an die OpenWB schicken.
                            if self.actionURL != '' and self.soc < (oldSoc-2):
                                # es gibt einen shelly, der angesteuert werden soll und
                                # neuer SoC ist hinreichend kleiner als der SoC vom Losfahren
                                # -> Zeichen, daß Fahrzeug gefahren wurde
                                logging.info(f'Rufe Licht-URL {self.actionURL} auf')
                                with urllib.request.urlopen(self.actionURL) as response:
                                    status = response.read()
                                    logging.debug(f'Antwort ist {status}')
                        except Exception as e:
                            logging.error(f'Schreiben des SOC an die Wallbox ist fehlgeschlagen: {e}')
                elif self.payload[0] == self.ODO_RESP_ID:
                    self.calcODO(self.payload)
                    logging.debug(f'Fahrzeug-Kilometerstand ist {self.odo}')

class eUp(carclass):
    # Alle Objekte werden nicht in Init initialisiert und sind deshalb Klassenobjekte!
    # wenn sie ihre Werte in der Klasse geändert werden, ändern sie sich in allen Instanzen!
    SPEAKS_UDS = True
    SOC_REQ_ID = 2021
    SOC_RESP_ID = 2029
    SOC_REQ_DATA = [3, 34, 2, 140, 170, 170, 170, 170]
    ODO_REQ_ID = 2021
    ODO_RESP_ID = 2029
    ODO_REQ_DATA = [3, 34, 2, 189, 170, 170, 170, 170]
    SOC_REQUEST = '{ "bus": "0", "type": "tx", "frame": [{ "id": '+str(SOC_REQ_ID)+', "dlc": 8, "rtr": false, "extd": false, "data": '+str(SOC_REQ_DATA)+' }] }'
    ODO_REQUEST = '{ "bus": "0", "type": "tx", "frame": [{ "id": '+str(ODO_REQ_ID)+', "dlc": 8, "rtr": false, "extd": false, "data": '+str(ODO_REQ_DATA)+' }] }'
        
    def calcSOC(self, bytes):
        logging.debug(f'Daten für SoC-Berechnung: {bytes}')
        self.soc = bytes[4]/2.5*51/46-6.4         # VW e-up [2029, 98, 2, 140, aa, xx, xx, xx, xx].

    def calcODO(self, bytes):
        logging.debug(f'Daten für ODO-Berechnung: {bytes}')
        self.odo =  bytes[5]*65536+bytes[6]*256+bytes[7] # VW e-up. [2029, 98, 2, 189, xx, bb, cc, dd, xx, xx]
        if self.odo == 0xffffff:
            self.odo = -1

class eGolf(carclass):
    SPEAKS_UDS = True
    SOC_REQ_ID = 2021
    SOC_RESP_ID = 2029
    SOC_REQ_DATA = [3, 34, 2, 140, 170, 170, 170, 170]
    ODO_REQ_ID = 2021
    ODO_RESP_ID = 2029
    ODO_REQ_DATA = [3, 34, 2, 189, 170, 170, 170, 170]
    SOC_REQUEST = '{ "bus": "0", "type": "tx", "frame": [{ "id": '+str(SOC_REQ_ID)+', "dlc": 8, "rtr": false, "extd": false, "data": '+str(SOC_REQ_DATA)+' }] }'
    ODO_REQUEST = '{ "bus": "0", "type": "tx", "frame": [{ "id": '+str(ODO_REQ_ID)+', "dlc": 8, "rtr": false, "extd": false, "data": '+str(ODO_REQ_DATA)+' }] }'

    def calcSOC(self, bytes):
        # Umrechnung gemäß https://github.com/meatpiHQ/wican-fw/issues/168#issuecomment-2325270376
        logging.debug(f'Daten für SoC-Berechnung: {bytes}')
        self.soc = max( [(bytes[4]-20)/2.2 , 0] ) # e-Golf [2029, 98, 2, 140, aa, xx, xx, xx, xx].

    def calcODO(self, bytes):
        logging.debug(f'Daten für ODO-Berechnung: {bytes}')
        self.odo = bytes[5]*65536+bytes[6]*256+bytes[7] # VW e-Golf, ungetestet. [2029, 98, 2, 189, xx, bb, cc, dd, xx, xx, xx, xx, xx, xx]
        if self.odo == 0xffffff:
            self.odo = -1

class VwMEB(carclass):
    SPEAKS_UDS = True
    SOC_REQ_ID = 0x17FC007B
    SOC_RESP_ID = 0x17FE007B
    SOC_REQ_DATA = [3, 34, 2, 140, 170, 170, 170, 170]
    ODO_REQ_ID = 0x17FC0076
    ODO_RESP_ID = 0x17FE0076
    ODO_REQ_DATA = [3, 34, 41, 90, 170, 170, 170, 170]
    SOC_REQUEST = '{ "bus": "0", "type": "tx", "frame": [{ "id": '+str(SOC_REQ_ID)+', "dlc": 8, "rtr": false, "extd": true, "data": '+str(SOC_REQ_DATA)+' }] }'
    ODO_REQUEST = '{ "bus": "0", "type": "tx", "frame": [{ "id": '+str(ODO_REQ_ID)+', "dlc": 8, "rtr": false, "extd": true, "data": '+str(ODO_REQ_DATA)+' }] }'

    def calcSOC(self, bytes):
        logging.debug(f'Daten für SoC-Berechnung:{bytes}')
        self.soc = round(bytes[4]/2.5*51/46-6.4) # VW MEB [0x17FE007B, 98, 2, 140, aa, xx, xx, xx]. SOC ist aa/2.5, Umrechnung auf Anzeigewert

    def calcODO(self, bytes):
        logging.debug(f'Daten für ODO-Berechnung:{bytes}')
        self.odo = bytes[4]*65536+bytes[5]*256+bytes[6] # VW MEB. [0x17FE0076, 98, 41, 90, aa, bb, cc, xx]
        if self.odo == 0xffffff:
            # Abfangen von "nicht bereit"
            self.odo = -1

class Fiat500e(carclass):
    SPEAKS_UDS = True
    SOC_REQ_ID = 0x18DA44F1
    SOC_RESP_ID = 0x18DAF144
    SOC_REQ_DATA = [3, 34, 160, 16, 170, 170, 170, 170]
    ODO_REQ_ID = 0x18DA42F1
    ODO_RESP_ID = 0x18DAF142
    ODO_REQ_DATA = [3, 34, 32, 1, 170, 170, 170, 170]
    SOC_REQUEST = '{ "bus": "0", "type": "tx", "frame": [{ "id": '+str(SOC_REQ_ID)+', "dlc": 8, "rtr": false, "extd": true, "data": '+str(SOC_REQ_DATA)+' }] }'
    ODO_REQUEST = '{ "bus": "0", "type": "tx", "frame": [{ "id": '+str(ODO_REQ_ID)+', "dlc": 8, "rtr": false, "extd": true, "data": '+str(ODO_REQ_DATA)+' }] }'

    def calcSOC(self, bytes):
        print(f'Daten für SoC-Berechnung:{bytes}')
        logging.debug(f'Daten für SoC-Berechnung:{bytes}')
        displaySoc = min( round(bytes[6]*0.45-6.4), 100 ) # Fiat 500e [0x18DAF144, 98, 160, 16, xx, xx, aa, xx, xx, xx, ...]. SOC ist aa/2.55
        return(displaySoc)
    def calcODO(self, bytes):
        logging.debug(f'Daten für ODO-Berechnung:{bytes}')
        self.odo = (bytes[4]*65536+bytes[5]*256+bytes[6])/10  # Fiat 500e [0x18DAF142, 98, 32, 1, aa, bb, cc, xx]
        if self.odo == 0xffffff / 10:
            self.odo = -1

# Ora Funky Cat, Danke an Kitmgue
class OraFunkyCat(carclass):
    SPEAKS_UDS = True
    SOC_REQ_ID = 1931
    SOC_RESP_ID = 1995
    SOC_REQ_DATA = [3, 34, 3, 8, 170, 170, 170, 170]
    ODO_REQ_ID = 1931
    ODO_RESP_ID = 1995
    ODO_REQ_DATA = [3, 34, 208, 4, 170, 170, 170, 170]
    SOC_REQUEST = '{ "bus": "0", "type": "tx", "frame": [{ "id": '+str(SOC_REQ_ID)+', "dlc": 8, "rtr": false, "extd": false, "data": '+str(SOC_REQ_DATA)+' }] }'
    ODO_REQUEST = '{ "bus": "0", "type": "tx", "frame": [{ "id": '+str(ODO_REQ_ID)+', "dlc": 8, "rtr": false, "extd": false, "data": '+str(ODO_REQ_DATA)+' }] }'

    # car specific functions
    def calcSOC(self, bytes):
        print(f'Daten für SoC-Berechnung:{bytes}')
        logging.debug(f'Daten für SoC-Berechnung:{bytes}')
        return( round((bytes[4]*256+bytes[5])/10) ) # Ora Funky Cat [1995, 98, 3, 8, aa, bb, xx, xx]. SOC ist (aa*256+bb)/10
    def calcODO(self, bytes):
        logging.debug(f'Daten für ODO-Berechnung:{bytes}')
        self.odo =  bytes[4]*65536+bytes[5]*256+bytes[6]  # Ora Funky Cat. [1995, 98, 208, 4, aa, bb, cc, xx]
        if self.odo == 0xffffff:
            # Abfangen von "nicht bereit"
            self.odo = -1

#see https://github.com/meatpiHQ/wican-fw/issues/17#issuecomment-1456925171
class ZoePH1(carclass):
    # Ich vermute, die alte Zoe spricht kein UDS. Sie sendet aber etliche CAN-Botschaften periodisch auf den CAN der OBD-Buchse.
    SPEAKS_UDS = False
    SOC_RESP_ID = 1070 # sollte Anzeige-SOC enthalten in Bytes 0 und 1
    ODO_RESP_ID = 1495 # enthält odometer in Bytes 2 bis 5

    def calcSOC(self, bytes):
        # Nach EVNotiPi: (msg[0:2]) >> 3 & 0x1fff) * 0.02 - also die oberen 13 Bits von Byte 0 und 1 der Nutzdaten, geteilt durch 50.
        logging.debug(f'Daten für SoC-Berechnung:{bytes}')
        self.soc = round( (bytes[1]*256 + (bytes[2]&0xf8) ) / 400) #erwartet: [1070,aa,bb,xx,xx,xx,xx,xx,xx] mit (aa*256+bb)/400

    def calcODO(self, bytes):
        # Nach EVNotiPi: (msg[2:6]) >> 4) * 0.01
        logging.debug(f'Daten für ODO-Berechnung:{bytes}')
        self.odo = round( (bytes[3]*16777216+bytes[4]*65536+bytes[5]*256+bytes[6])/1600 )  # erwartet: [1495, xx, xx,  aa, bb, cc, dd, xx] mit odo=aa*2**24+bb*2**16+cc*256+dd

# see https://github.com/iternio/ev-obd-pids/blob/main/renault/zoe2.json
class ZoePH2(carclass):
    SPEAKS_UDS = True
    SOC_REQ_ID =  14343153  # DADBF1
    SOC_RESP_ID = 417001947 # 18DAF1DB
    SOC_REQ_DATA = [3, 34, 144, 2, 170, 170, 170, 170] # Request 0x229002
    ODO_REQ_ID = 0 # nicht abfragen. sonst: 1859 (0x743) - Instrument cluster
    ODO_RESP_ID = 0
    ODO_REQ_DATA = [3, 34, 2, 6, 170, 170, 170, 170]
    SOC_REQUEST = '{ "bus": "0", "type": "tx", "frame": [{ "id": '+str(SOC_REQ_ID)+', "dlc": 8, "rtr": false, "extd": true, "data": '+str(SOC_REQ_DATA)+' }] }'
    ODO_REQUEST = '{ "bus": "0", "type": "tx", "frame": [{ "id": '+str(ODO_REQ_ID)+', "dlc": 8, "rtr": false, "extd": true, "data": '+str(ODO_REQ_DATA)+' }] }'

    def calcSOC(self, bytes):
        # Renault Zoe, siehe https://github.com/nickn17/evDash/blob/master/src/CarRenaultZoe.cpp
        # Antwort auf SOC: "2103": 01D 6103018516A717240000000001850185000000FFFF07D00516E60000030000000000
        # "2103", 29 Bytes 61030185 16A71724 00000000 01850185 000000FF FF07D005 16E60000 03000000 0000
        # liveData->params.socPerc = liveData->hexToDecFromResponse(48, 52, 2, false) / 100.0; 48 und 52 sind Nibbles? Byte 24 bis 26
        # 6103 ist der Request +0x40 im ersten Byte
        logging.debug(f'Daten für SoC-Berechnung:{bytes}')
        self.soc = round( (bytes[x]*256+bytes[y]) / 100)

    def calcODO(self, bytes):
        #SOC_RESP_ID = ??#(Antwortstring in hex scheint mindestens 52 Bytes lang zu sein?! 
        # Antwort auf ODO: "220206", // 62020600015459
        logging.debug(f'Daten für ODO-Berechnung:{bytes}')
        self.odo = bytes[4]*65536+bytes[5]*256+bytes[6]
        if self.odo == 0xffffff:
            # Abfangen von "nicht bereit"
            self.odo = -1

class StandardFuelLevel(carclass):
    # Warum nicht den relativen Tankfüllstand als SOC an die OpenWB senden? Hier die Lösung für den Golf
    SPEAKS_UDS = True
    SOC_REQ_ID = 2016 # Motorelektronik, Standard-PID für rel. Tankfüllstand
    SOC_RESP_ID = 2024
    SOC_REQ_DATA = [2, 1, 47, 0, 0, 0, 0, 0]
    ODO_REQ_ID = 1812    # Odometer Verbrenner-Golf, Schalttafeleinsatz
    ODO_RESP_ID = 1918
    ODO_REQ_DATA = [3, 34, 34, 3, 0, 0, 0, 0]
    SOC_REQUEST = '{ "bus": "0", "type": "tx", "frame": [{ "id": '+str(SOC_REQ_ID)+', "dlc": 8, "rtr": false, "extd": false, "data": '+str(SOC_REQ_DATA)+' }] }'
    ODO_REQUEST = '{ "bus": "0", "type": "tx", "frame": [{ "id": '+str(ODO_REQ_ID)+', "dlc": 8, "rtr": false, "extd": false, "data": '+str(ODO_REQ_DATA)+' }] }'

    def calcSOC(self, bytes):
        logging.debug(f'Daten für Tankfüllstand: {bytes}')
        self.soc = bytes[3]/2.0 # Standard-PID Tankfüllstand [2024, 65, 47, aa, xx, xx, xx, xx, xx]. Füllstand=aa/2.0

    def calcODO(self, bytes):
        logging.debug(f'Daten für ODO-Berechnung: {bytes}')
        self.odo = bytes[4]*65536 + bytes[5]*256 + bytes[6] # km-Stand vom Schalttafeleinsatz [1918, 98, 34, 34, aa, bb, cc, xx, xx]
        if self.odo == 0xffff * 10:
            # Abfangen von "nicht bereit"
            self.odo = -1


"""
class SmartED(carclass):
    # zu prüfen: Kann man per UDS die nötigen Botschaften anfordern oder nutzt OVMS den rohen CAN? Anscheinend
    # wartet OVMS einfach, bis die Daten eintreffen? Kann man WiCAN zum rohen Durchleiten bringen?
    # SoC würde unter CAN-ID 1304 eintreffen mit 8 Datenbytes
    # see https://github.com/MyLab-odyssey/ED_BMSdiag/blob/master/ED_BMSdiag/canDiag.cpp
    #     https://github.com/MyLab-odyssey/ED_BMSdiag/blob/master/ED_BMSdiag/_BMS_dfs.h
    SOC_REQ_ID = 0	# do not send a SoC request at WiCAN arrival
    SOC_RESP_ID = 1304
    SOC_REQ_DATA = [1,2,3,4,5,6,7,8]
    ODO_REQ_ID = 0	# do not send a ODO request
    ODO_RESP_ID = 1042
    ODO_REQ_DATA = [2, 1, 166, 170, 170, 170, 170, 170]
    SOC_REQUEST = '{ "bus": "0", "type": "tx", "frame": [{ "id": '+str(SOC_REQ_ID)+', "dlc": 8, "rtr": false, "extd": false, "data": '+str(SOC_REQ_DATA)+' }] }'
    ODO_REQUEST = '{ "bus": "0", "type": "tx", "frame": [{ "id": '+str(ODO_REQ_ID)+', "dlc": 8, "rtr": false, "extd": false, "data": '+str(ODO_REQ_DATA)+' }] }'

    # car specific functions
    def calcSOC(self, bytes):
        print(f'Daten für SoC-Berechnung:{bytes}')
        logging.debug(f'Daten für SoC-Berechnung:{bytes}')
        self.soc = round( (bytes[8]/2) ) # Smart ED [1304, ?, ?, ?, xx, xx, xx, xx, aa]. Displayed SOC ist aa/2
        #return( round( ( (bytes[5] & 3)*256 + bytes[6] ) /10) ) # Smart ED [725, ?, ?, ?, xx, aa, bb, xx, xx]. real SOC is ((2lower Bits of aa)*256+bb)/10
    def calcODO(self, bytes):
        logging.debug(f'Daten für ODO-Berechnung:{bytes}')
        self.odo = ( bytes[3]*65536+bytes[4]*256+bytes[5] ) # Smart ED [1042, xx, xx, aa, bb, cc, dd, xx, xx]
        if self.odo == 0xffffff:
            # Abfangen von "nicht bereit"
            self.odo = -1
"""
