# Bitte in den folgenden Zeilen nichts ändern!
import cars
import chargepoints

myCars = []     	# leere Liste von Fahrzeugen
myChargepoints = []	# leere Liste von Ladepunkten

"""
Eigene Änderungen ab hier

Definition der Fahrzeuge

Erklärung: myCars wir die Liste der mit WiCAN-Steckern betriebenen Fahrzeuge. Es werden mittels myCars.append() Fahzeuge an diese Liste angehängt.
Die Fahrzeugklassen ("Fahrzeugtypen") sind in cars.py definiert. Momentan verfügbar:
    eUp,
    eGolf,
    VwMEB,
    Fiat500e,
    OraFunkyCat,
    ZoePH1 (R210/Q210,R240,R75,R90,Q90 - kein Kilometerstand, keinSpritmonitor!)
    StandardFuelLevel (Standard-PID für Tankfüllstand eines Verbrenners und Kilometerstand, nur zur Anzeige in der Wallbox)

Für jeden Fahrzeugtyp muss mindestens definiert sein:
name - Der Name, der auch im WiCAN vergeben ist.
openwbVehicleId - die dem Fahrzeug zugeordnete openwb-ID (Nummer), auf der Statusseite der Wallbox angezeigt.

Definition eines Fahrzeugs, das nicht an Spritmonitor übermitteln soll:
myCars.append(cars.VwMEB(
    name = "Standard",                 # Name des Fahrzeugs, wie im WiCAN konfiguriert. Definiert einen Zweig unter others/ im MQTT-Broker.
    openwbVehicleId = 0                # Fahrzeugnummer in der OpenWB-Konfiguration
))

Soll an Spritmonitor übermittelt werden, sind weitere Parameter erforderlich (Fahrzeug muss bei spritmonitor angelegt sein!):
useSpritmonitor - muss True gesetzt werden
spritmonitorVehicleId - Fahrzeugnummer, die das Fahrzeug bei spritmonitor hat
spritmonitorFuelsort - Stromsorte; 19 für Strom, 24 für Ökostrom
spritmonitorFuelprice - Strompreis in €/kWh. Im Winter Bezugspreis, im Sommer bei vorhandener PV z.B. Einspeisevergütung oder Gestehungskosten
spritmonitorAttributes - Attribute wie summertires oder ac, die per Default gesetzt werden sollen, siehe Dokumentation

Definition eines Fahrzeuges, das zu Spritmonitor übermitteln soll:
myCars.append(cars.eUp(
    name = "nulli",
    openwbVehicleId = 1,
    useSpritmonitor = True,
    spritmonitorVehicleId =  1370192,
    spritmonitorFuelsort = 24,
    spritmonitorFuelprice = 0.08,
    spritmonitorAttributes = 'summertires,slow'
))

Wichtig für Spritmonitor-Konfiguration: Es muß eine gültige Umgebungsvariable
SPRITMONITOR_BEARER_TOKEN geben. Diese kann bei Spritmonitor.de auf der Passwort-
Vergessen-Seite angefordert werden. Eine Umgebungsvariable wird verwendet, damit
nicht aus versehen der Zugang mit verschickt wird, wenn der Code weitergegeben
oder veröffentlicht wird. Sie wird vor Aufruf von soc_helper.py mittels
"export SPRITMONITOR_BEARER_TOKEN=<eigenerToken>" deklariert - idealerweise in der Datei
~/.profile schon bei der Anmeldung am System.
"""
myCars.append(cars.eUp(
    name = 'nulli',
    openwbVehicleId = 1,
    useSpritmonitor = True,
#    spritmonitorVehicleId =  1370192,
    spritmonitorVehicleId =  1569502,
    spritmonitorFuelsort = 24,
    spritmonitorFuelprice = 0.08,
    spritmonitorAttributes = 'summertires,slow'
))

myCars.append(cars.StandardFuelLevel(
    name = 'golfi',                    # Name des Fahrzeugs, wie im WiCAN konfiguriert. Definiert einen Zweig unter others/ im MQTT-Broker.
    openwbVehicleId = 3                # Fahrzeugnummer in der OpenWB-Konfiguration
))

#myCars.append(cars.eUp(
#    name = 'Standard',                 # Name des Fahrzeugs, wie im WiCAN konfiguriert. Definiert einen Zweig unter others/ im MQTT-Broker.
#    openwbVehicleId = 0                # Fahrzeugnummer in der OpenWB-Konfiguration
#))

#myCars.append(cars.VwMEB(
#    name = 'Fremdfahrzeug',            # Name des Fahrzeugs, wie im WiCAN konfiguriert. Definiert einen Zweig unter others/ im MQTT-Broker.
#    openwbVehicleId = 2                # Fahrzeugnummer in der OpenWB-Konfiguration
#))

"""
Definition der Ladepunkte.
Die chargepointId ist der Statusseite zu entnehmen.
"""
myChargepoints.append(chargepoints.chargepoint(chargepointId=3))
# Für jeden weiteren Ladepunkt eine weitere Zeile mit der jeweiligen ID anfügen

"""
#OPENWB-Konfiguration
"""
OPENWB_IP = '192.168.1.102'   # hier die Adresse der OpenWB einstellen - Lokaler Name könnte auch funktionieren, nicht ausprobiert

"""
Sonstiges
"""
# Zum Loglevel:
# CRITICAL - momentan nur Versionsausgabe bei Start
# ERROR - Fehler
# WARNING - nur Dinge, die auffällig sind und wichtiger
# INFO - Überblick, was gerade so passiert
# DEBUG - Zur Entwicklung.
LOGLEVEL = 'INFO'
# In das Chargelog werden die Daten der Ladevorgänge geschrieben: Start-SOC, Kilometerstand, Energiemenge, End-SOC laut Wallbox
# Bitte den Pfad anpassen (User, soc_helper-Verzeichnis!)
CHARGELOG_PATH = '/home/pi/soc_helper/energydata.csv'

