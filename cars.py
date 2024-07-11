"""
cars.py
Definiert die OBD2-Kommandos der zur Auswahl stehenden Fahrzeuge und baut aus den Angaben in configuration.py mit den OBD2-Kommandos
für jeden Fahrzeugtyp eine Fahrzeugklasse zusammen.
"""

from dataclasses import dataclass, field
from typing import List
import logging
import json

validCars = ("eUp", "eGolf", "VwMEB", "Fiat500e", "OraFunkyCat", "Zoe", "StandardFuelLevel")

@dataclass
class carclass:
    # Vorlage für die Nutzerdaten aller Fahrzeugklassen.
    name: str = 'UnnamedCar'
    openwbVehicleId: int = 1
    useSpritmonitor: bool = False
    spritmonitorVehicleId: int = 0
    spritmonitorFuelsort: int = 19
    spritmonitorFuelprice: float = 0.27
    spritmonitorAttributes: str = 'summertires, slow'
    odo: float = 0					# Letzter vom Fahrzeug empfangener Kilometerstand
    soc: float = 0					# Letzter vom Fahrzeug emfangener SoC
    openwbsoc: float = 0            # Letzter von der Wallbox empfangener (berechneter) SoC
        
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
                logging.info(f'Fahrzeug {self.name} ist online. Sende SOC- und ODO-Anforderung')

                if self.SOC_REQ_ID == 0:
                    logging.info(f'SOC_REQ_ID ist 0, sende keine Anforderung')
                else:
                    logging.info(f'Sende SOC-Anforderung: {self.SOC_REQUEST}')
                    client.publish(self.getTxTopic(), self.SOC_REQUEST)

                if self.ODO_REQ_ID == 0:
                    logging.info(f'ODO_REQ_ID ist 0, sende keine Anforderung')
                else:
                    logging.info(f'Sende ODO-Anforderung: {self.ODO_REQUEST}')
                    client.publish(self.getTxTopic(), self.ODO_REQUEST)
            else:
                logging.info(f'Fahrzeug {self.name} ist <<offline>>')
        except Exception as e:
            logging.warning(f'Fehler beim Parsen der Statusnachricht: {e}')
        
    def cb_getOpenwbSoc(self, client, userdata, msg):
        logging.debug(f'cb_getOpenwbSoc von Fahrzeug {self.name} aufgerufen')
        try:
            self.openwbsoc = float(msg.payload)
        except Exception as e:
            logging.warn(f'Fahrzeug {self.name}: Konnte von der Wallbox empfangenen SoC nicht in Zahl umwandeln: {e}')
            self.openwbsoc = 0
        logging.debug(f'Von der Wallbox für Fahrzeug {self.name} empfangener SoC: {self.openwbsoc}')
        return()
        
    def cb_rx(self, client, userdata, msg):
        # Callback-Funktion für eine CAN-Rx-Botschaft. Prüft, ob es eine SOC- oder ODO-haltige Botschaft ist
        # und sendet im Fall eines SOC den Wert zur OpenWB. Mehrteilige Botschaften werden aneinander gehängt.
        logging.debug(f'cb_rx von Fahrzeug {self.name} aufgerufen')
        logging.debug(f'Empfangene CAN-Botschaft: {msg.payload}')
        try:
            frame = json.loads(msg.payload)['frame'][0]
            # json.loads(msg.payload): String der Nutzlast als dict
            # json.loads(msg.payload)['frame']: Datenframe in f ergibt eine Liste mit einem Element
            # json.loads(msg.payload)['frame'][0]: Das nullte und einzige Element der Liste ist ein dict
            id = frame['id']        # json.loads(msg.payload)['frame'][0]['id']: Sender-ID
            data = frame['data']    # json.loads(msg.payload)['frame'][0]['data']: Liste der Nutzbytes vom CAN
        except Exception as e:
            logging.error(f'Fehler beim json-Parsen der empfangenen CAN-Botschaft: {e}')
    
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
            # FIXME: Wenn hier kein erster Teil vorhanden ist, sondern unmotiviert ein zweiter kommt, knallt es. Momentan bei
            # StandardFuelLevel so mit Golf7, der immer wieder ein [32,16,0,0,0,0,0,0] sendet, warum auch immer
            if hasattr(self, 'payload') and hasattr(self, 'bytesToReceive'):
                self.payload.extend(data[1:8])     # Je Nachfolger sollten 7 Nutzbytes kommen
                self.bytesReceived += 7
                if self.bytesReceived >= self.bytesToReceive:
                    self.messageComplete = True
                    self.bytesToReceive = 0
                logging.debug(f'Mehrteilige Botschaft komplett: {self.payload}')
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
            # Erwartungswerte zusammenbauen
            lenSOC = self.SOC_REQ_DATA[0]
            expectSOC = self.SOC_REQ_DATA[1:1+lenSOC]
            expectSOC[0] += 64
            logging.debug(f'lenSOC: {lenSOC}; expectSOC: {expectSOC}')
            lenODO = self.ODO_REQ_DATA[0]
            expectODO = self.ODO_REQ_DATA[1:1+lenODO]
            expectODO[0] += 64
            logging.debug(f'lenODO: {lenODO}; expectODO: {expectODO}')
            if self.payload[0] == self.SOC_RESP_ID and self.payload[1:1+lenSOC] == expectSOC:
                self.calcSOC(self.payload)
                if self.soc is None:
                    logging.warning("Erhaltener SOC ist ungültig (Return-Wert None). Wird ignoriert")
                elif self.soc<0 or self.soc>100:
                    logging.warning(f'Erhaltener SOC {soc} ist ungültig. Wird ignoriert.')
                else:
                    logging.info(f'Fahrzeug-SOC ist {self.soc}')
                    logging.debug(f'SOC-Wert von {self.soc} an {self.getsetSocTopic()} schicken.')
                    try:
                        client.publish(self.getsetSocTopic(), self.soc)     #SOC-Wert an die OpenWB schicken.
                    except Exception as e:
                        logging.error(f'Schreiben des SOC an die Wallbox ist fehlgeschlagen: {e}')
            elif self.payload[0] == self.ODO_RESP_ID and self.payload[1:1+lenODO] == expectODO:
                self.calcODO(self.payload)
                logging.info(f'Fahrzeug-Kilometerstand ist {self.odo}')
            else:
                logging.warning(f'Empfangene Botschaft: {self.payload} ist keine gültige Antwort auf eine konfigurierte Anfrage')

class eUp(carclass):
    # Alle Objekte werden nicht in Init initialisiert und sind deshalb Klassenobjekte!
    # wenn sie ihre Werte in der Klasse geändert werden, ändern sie sich in allen Instanzen!
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
        self.soc = round(bytes[4]/2.5*51/46-6.4)         # VW e-up [2029, 98, 2, 140, aa, xx, xx, xx, xx].

    def calcODO(self, bytes):
        logging.debug(f'Daten für ODO-Berechnung: {bytes}')
        self.odo =  bytes[5]*65536+bytes[6]*256+bytes[7] # VW e-up. [2029, 98, 2, 189, xx, bb, cc, dd, xx, xx]

class eGolf(carclass):
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
        self.soc = round((bytes[4]/2.5-8)/0.88) # e-Golf [2029, 98, 2, 140, aa, xx, xx, xx, xx]. SOC=aa/2.5, Umrechung auf Anzeigewert

    def calcODO(self, bytes):
        logging.debug(f'Daten für ODO-Berechnung: {bytes}')
        self.odo = bytes[5]*65536+bytes[6]*256+bytes[7] # VW e-Golf, ungetestet. [2029, 98, 2, 189, xx, bb, cc, dd, xx, xx, xx, xx, xx, xx]

class VwMEB(carclass):
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

class Fiat500e(carclass):
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
        print(f'Daten für ODO-Berechnung:{bytes}')
        logging.debug(f'Daten für ODO-Berechnung:{bytes}')
        return( (bytes[4]*65536+bytes[5]*256+bytes[6])/10 ) # Fiat 500e [0x18DAF142, 98, 32, 1, aa, bb, cc, xx]


# Ora Funky Cat, Danke an Kitmgue
class OraFunkyCat(carclass):
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
        print(f'Daten für ODO-Berechnung:{bytes}')
        logging.debug(f'Daten für ODO-Berechnung:{bytes}')
        return( bytes[4]*65536+bytes[5]*256+bytes[6] ) # Ora Funky Cat. [1995, 98, 208, 4, aa, bb, cc, xx]

# see https://github.com/nickn17/evDash/blob/master/src/CarRenaultZoe.cpp
class Zoe(carclass):
    SOC_REQ_ID = 1947 # 0x79B
    SOC_RESP_ID = 1955 # 0x7A3 (nicht erwähnt normal sendeID+8)
    SOC_REQ_DATA = [2, 33, 3, 170, 170, 170, 170, 170] # Request 0x2103
    ODO_REQ_ID = 1859 # 0x743 - Instrument cluster
    ODO_RESP_ID = 1867 # 0x74B (nicht erwähnt normal sendeID+8)
    ODO_REQ_DATA = [3, 34, 2, 6, 170, 170, 170, 170] # Request 0x220206
    SOC_REQUEST = '{ "bus": "0", "type": "tx", "frame": [{ "id": '+str(SOC_REQ_ID)+', "dlc": 8, "rtr": false, "extd": false, "data": '+str(SOC_REQ_DATA)+' }] }'
    ODO_REQUEST = '{ "bus": "0", "type": "tx", "frame": [{ "id": '+str(ODO_REQ_ID)+', "dlc": 8, "rtr": false, "extd": false, "data": '+str(ODO_REQ_DATA)+' }] }'

    def calcSOC(self, bytes):
        # "2103", // 01D 6103018516A717240000000001850185000000FFFF07D00516E60000030000000000, Ziffern 48,49,50,51
        # "2103", 29 Bytes, 61030185 16A71724 00000000 01850185 000000FF FF07D005 16E60000 03000000 0000 -> 16E6, entspricht 58,62%
        logging.debug(f'Daten für SoC-Berechnung:{bytes}')
        self.soc = round( (bytes[21]*256+bytes[22]) / 100) #erwartet: [1955, 61,03,...]

    def calcODO(self, bytes):
        # "220206", // 620206 00 01 54 59
        logging.debug(f'Daten für ODO-Berechnung:{bytes}')
        self.odo = bytes[4]*16777216+bytes[5]*65536+bytes[6]*256+bytes[7] # erwartet: [1867, 94, 2, 6, aa, bb, cc, dd, xx] mit odo=aa*2**24+bb*2**16+cc*256+dd

class StandardFuelLevel(carclass):
    # Warum nicht den relativen Tankfüllstand als SOC an die OpenWB senden? Hier die Lösung für 11-Bit-CAN-IDs:
    SOC_REQ_ID = 2016
    SOC_RESP_ID = 2024
    SOC_REQ_DATA = [2, 1, 47, 0, 0, 0, 0, 0]
    ODO_REQ_ID = 2016    # Odometer; im Verbrenner-eUp oder -Golf leider nicht vorhanden
    ODO_RESP_ID = 2024
    ODO_REQ_DATA = [2, 1, 166, 0, 0, 0, 0, 0]
    SOC_REQUEST = '{ "bus": "0", "type": "tx", "frame": [{ "id": '+str(SOC_REQ_ID)+', "dlc": 8, "rtr": false, "extd": false, "data": '+str(SOC_REQ_DATA)+' }] }'
    ODO_REQUEST = '{ "bus": "0", "type": "tx", "frame": [{ "id": '+str(ODO_REQ_ID)+', "dlc": 8, "rtr": false, "extd": false, "data": '+str(ODO_REQ_DATA)+' }] }'

    def calcSOC(self, bytes):
        logging.debug(f'Daten für Tankfüllstand: {bytes}')
        self.soc = bytes[3]/2.55 # Standard-PID Tankfüllstand [2024, 65, 47, aa, xx, xx, xx, xx, xx]. Füllstand=aa/2.55

    def calcODO(self, bytes):
        logging.debug(f'Daten für ODO-Berechnung: {bytes}')
        self.odo = ( bytes[3]*16777216 + bytes[4]*65536 + bytes[5]*256 + bytes[6] ) # Standard-PID 166 vom MSG [2024, 65, 166, aa, bb, cc, dd, xx, xx]


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
        print(f'Daten für ODO-Berechnung:{bytes}')
        logging.debug(f'Daten für ODO-Berechnung:{bytes}')
        self.odo = ( bytes[3]*65536+bytes[4]*256+bytes[5] ) # Smart ED [1042, xx, xx, aa, bb, cc, dd, xx, xx]

# see https://github.com/iternio/ev-obd-pids/blob/main/renault/zoe.json
class Zoe(carclass):
    SOC_REQ_ID = 2020 # 0x7E4
    SOC_RESP_ID = 2028 # 0x7EC
    SOC_REQ_DATA = [3, 34, 32, 2, 170, 170, 170, 170] # Request 0x222002
    ODO_REQ_ID = 1859 # 0x743 - Instrument cluster
    ODO_RESP_ID = ?
    ODO_REQ_DATA = [3, 34, 2, 6, 170, 170, 170, 170]
    SOC_REQUEST = '{ "bus": "0", "type": "tx", "frame": [{ "id": '+str(SOC_REQ_ID)+', "dlc": 8, "rtr": false, "extd": false, "data": '+str(SOC_REQ_DATA)+' }] }'
    ODO_REQUEST = '{ "bus": "0", "type": "tx", "frame": [{ "id": '+str(ODO_REQ_ID)+', "dlc": 8, "rtr": false, "extd": false, "data": '+str(ODO_REQ_DATA)+' }] }'

    def calcSOC(self, bytes):
        # "2103", 29 Bytes 61030185 16A71724 00000000 01850185 000000FF FF07D005 16E60000 03000000 0000
        logging.debug(f'Daten für SoC-Berechnung:{bytes}')
        self.soc = round( (bytes[25]*256+bytes[26]) / 50)

    def calcODO(self, bytes):
        #SOC_RESP_ID = ??#(Antwortstring in hex scheint mindestens 52 Bytes lang zu sein?! 
        # Antwort auf ODO: "220206", // 62020600015459
        logging.debug(f'Daten für ODO-Berechnung:{bytes}')
        self.odo = bytes[4]*65536+bytes[5]*256+bytes[6]

#see https://github.com/iternio/ev-obd-pids/blob/main/renault/zoe2.json
class Zoe2(carclass):
    SOC_REQ_ID =  14342897 #DADAF1 (alternativ: 0x79B Lithium battery controller)
    SOC_RESP_ID = 417001947 # 18DAF1DB oder 18DADBF1?
    SOC_REQ_DATA = [3, 34, 144, 2, 170, 170, 170, 170] # Request (0x2103 oderr 0x229002?)
    ODO_REQ_ID = 1859 # 0x743 - Instrument cluster
    ODO_RESP_ID = ?
    ODO_REQ_DATA = [3, 34, 2, 6, 170, 170, 170, 170]
    SOC_REQUEST = '{ "bus": "0", "type": "tx", "frame": [{ "id": '+str(SOC_REQ_ID)+', "dlc": 8, "rtr": false, "extd": true, "data": '+str(SOC_REQ_DATA)+' }] }'
    ODO_REQUEST = '{ "bus": "0", "type": "tx", "frame": [{ "id": '+str(ODO_REQ_ID)+', "dlc": 8, "rtr": false, "extd": false, "data": '+str(ODO_REQ_DATA)+' }] }'

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
"""
