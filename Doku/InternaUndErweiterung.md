# Aufbau von soc_Helper und Erweiterung der bekannten Fahrzeuge
Folgende Dateien sind vorhanden:

1. soc_helper - das Hauptprogramm
1. cars.py - Fahrzeugspezifischer Code, Fahrzeugtypenklassen
1. chargepoints.py - Ladepunktspezifischer Code
1. energylog.py - Funktionalität zum lokalen Speichern der Ladevorgänge
1. spritmonitor.py - Verbindungscode zur Spritmonitor-Anbindung
1. startAtBoot.sh - Skript, das in die Nutzer-Crontab eingetragen werden
kann, um den soc_helper bei STart des Rechner mitzustarten

## soc_helper.py (Hauptprogramm)
Das Hauptprogramm tut folgendes:

1. Initialisiert den Logger,
1. prüft die Konfiguration in configuration.py,
1. öffnet die lokale Ladelogdatei,
1. Richtet einen MQTT-Client ein,
1. Verbindet die Callback-Funktionen der Ladepunkte und Fahrzeuge mit den
entsprechenden Topics und

## cars.py
In cars.py ist eine Grund-Fahrzeugklasse carclass definiert. Davon abgeleitet
werden pro Fahrzeugtyp eine Fahrzeugklasse. Jede Fahrzeuginstanz hat die
folgenden Variablen und Funktionen.

### Fahrzeug-Oberklasse carclass

#### Variablen
Folgende Variablen können in configuration.py fahrzeugindividuell gesetzt werden:

1. **name** - Fahrzeugname (wie im WiCAN definiert),
1. **openwbVehicleId** - OpenWB-ID des Fahrzeugs zur Zuordnung,
1. **useSpritmonitor** - Ob Spritmonitor verwendet werden soll
1. **spritmonitorVehicleId** - Fahrzeugnummer bei Spritmonitor
1. **spritmonitorFuelsort** - Stromart, die bei Spritmonitor angegeben wird
(Öko oder Dreckstrom)
1. **spritmonitorFuelprice** - Arbeitspreis, der bei Spritmonitor verwendet
wird
1. **spritmonitorAttributes** - Attribute für Spritmonitor (Reifenart,
Fahrweise, Klimaanlage usw)

Es werden einige Hilfsfunktionen definiert, die als Rückgabe einen String
mit jeweils einem MQTT-TOpic liefern:

1. **getStatusTopic()** liefert das MQTT-Topic für den WiCAN-Status des
jeweiligen Fahrzeugs
1. **getRxTopic(self)** liefert das MQTT-CAN-Empfangstopics für das Fahrzeug
1. **getTxTopic(self)** liefert das MQTT-CAN-Sendetopic für das Fahrzeug
1. **getgetSocTopic(self)** liefert das MQTT-Topic, mit dem der SoC des jeweiligen
Fahrzeuges aus der OpenWB gelesen werden kann.
1. **getsetSocTopic(self)** liefert das MQTT-Topic, mit dem der SoC für das
jeweilige Fahrzeug in die OpenWV geschrieben werden kann.

Die folgenden Callback-Funktionen definieren das Herz des soc_helpers. Sie
werden dem MQTT-Client bei Programmstart mitgegeben und aufgerufen, wenn die
entsprechenden Topics des OpenWB-MQTT-Brokers eine Nachricht empfangen:

#### cb_getOpenwbSoc(self, client, userdata, msg)
Diese Funktion wird aufgerufen, wenn vom WiCAN der zugehörigen
Fahrzeugklasse das Status-Topic beschrieben wird. Die Funktion prüft, ob der
Status 'online' ist. Ist dies der Fall, werden nacheinander die SoC- und
Odometer-Abfragen des Fahrzeugs an das WiCAN-Tx-Topic geschrieben.

Falls eine Request-ID 0 ist, wird die entsprechende Abfrage nicht gesendet.
Dies kann genutzt werden, wenn eine Abfrage für ein Fahrzeug noch nicht
bekannt ist und nur die andere genutzt werden soll.

#### cb_getOpenwbSoc(self, client, userdata, msg)
Diese Funktion wird aufgerufen, sobald ein SoC-Wert für das zugehörige
Fahrzeug von der Wallbox geschrieben wird. Es wird versucht, den Inhalt der
Botschaft (msg.payload) in eine Gleitkommazahl umzuwandeln und
Fahrzeugklassenintern zu speichern. Gelingt dies nicht, weil zum Beispiel noch
kein Wert hinterlegt ist, wird der Wert 0 angelegt.

#### cb_rx(self, client, userdata, msg)
Diese Funktion wird aufgerufen, wenn der WiCAN eine OBD-Botschaft des Fahrzeugs
empfangen hat. Diese Botschaft wird geprüft, ob sie eine Antwort auf eine
SoC- oder Odometer-Abfrage ist. Mehrteilige Botschaften werden vorher
zusammengesetzt.

Wenn eine gültige Antwort erkannt wird, wird die passende
Umrechnungsfunktion calcSOC oder calcODO des Fahrzeugs aufgerufen. Die
Umrechnungsfunktionen speichern ihr Ergebnis in der jeweiligen Instanz der
Fahrzeugklasse.

### Individuelle Fahrzeugklassen (Kind-Klassen)
Diese Klassen erben alle Objekte der Oberklasse carclass. Zusätzlich wird
Fahrzeugtypenindividueller Umfang festgelegt:

#### Variablen
qwe

#### Funktionen
asd

## chargepoints.py

## energylog.py

## spritmonitor.py

## Erweiterung um neue Fahrzeugtypen
