# Aufbau von soc_Helper und Erweiterung der bekannten Fahrzeuge

## Inhalt
Folgende Dateien sind vorhanden:

1. [soc_helper - das Hauptprogramm](#soc_helperpy)
1. [cars.py - Fahrzeugspezifischer Code, Fahrzeugtypenklassen](#carspy)
1. [chargepoints.py - Ladepunktspezifischer Code](#chargepointspy)
1. [energylog.py - Funktionalität zum lokalen Speichern der Ladevorgänge](#energylogpy)
1. [spritmonitor.py - Verbindungscode zur Spritmonitor-Anbindung](#spritmonitorpy)
1. [startAtBoot.sh - Skript, das in die Nutzer-Crontab eingetragen werden kann, um den soc_helper bei Start des Rechner mitzustarten](#startatbootsh)

## soc_helper.py
Das Hauptprogramm tut folgendes:

1. Initialisiert den Logger,
1. prüft die Konfiguration in configuration.py,
1. öffnet die lokale Ladelogdatei,
1. Richtet einen MQTT-Client ein,
1. Verbindet die Callback-Funktionen der Ladepunkte und Fahrzeuge mit den
entsprechenden Topics und wartet dann auf MQTT-Ereignisse

[zurück](#inhalt)

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

Die in den Fahrzeugindividuellen Klassen verwendeten Variablen sind für fast jeden Fahrzeugtyp unterschiedlich:
1. **SOC_REQ_ID**, **ODO_REQ_ID** - CAN-ID des OBD-Requests. Diese spricht das gemeinte Steuergerät an. Wenn der SoC oder das Odometer nicht abgefragt werden sollen, ist der entsprechende ID auf 0 zu setzen; in diesem Fall wird die zugehörige Abfrage nicht abgeschickt, wenn der Status des WiCAN auf online wechselt. Bei 11-Bit-IDs ist 0x7DF (2015) eine Broadcast-ID für bis zu 8 Steuergeräte. Es antwortet das Steuergerät, das sich angesprochen fühlt. Bitte keine Broadcast-ID verwenden: Da bei mehrteiligen Botschaften für die Anforderung "Continue" die korrekte Steuergeräte-ID verwendet werden muss, funktioniert eine Broadcast-ID in diesem Fall nicht.
2. **SOC_RESP_ID**, **ODO_RESP_ID** - CAN-ID der erwarteten Antwort. Bei 11-Bit-IDs ist die ID meist um 8 größer als die Request-ID.
3. **SOC_REQ_DATA** - eine Liste von 8 Datenbytes, die die eigentliche Abfrage des Soc darstellen. Das erste Byte steht für die Länge der Abfrage, die folgenden Bytes sind die Abfrage. Die Werte der restlichen Bytes sind egal.
4. **ODO_REQ_DATA** - wie SOC_REQ_DATA, für die Abfrage des Kilometerstandes
5. **SOC_REQUEST** - Der json-String, der die Abfrage für den SoC für den WiCAN zusammenbaut. Hier bitte lediglich den Wert für **"extd"** (true oder false) korrekt setzen und den Rest unverändert lassen: true, wenn die Request-ID einer erweiterte ID ist (29 Bits) und false, wenn eine 11-Bit-ID verwendet wird. Eine 11-Bit-ID kann maximal 2047 groß sein. wenn die oben genannten IDs größer sind, ist davon auszugehen, daß extd auf true gesetzt sein muß.
6. **ODO_REQUEST** - wie SOC_REQUEST, nur für das Odometer

#### calcSOC(self, bytes)
berechnet die Klassenvariable soc aus den Rohdaten, die in der Liste bytes übergeben wird. Der erste Wert in bytes ist entgegen dem Namen kein Byte, sondern der Wert SOC_RESP_ID. Die folgenden Bytes sind die zusammengefassten Nutzlasten der Antwort aus die SoC-Anfrage. Zunächst das Echo der Anfrage, wobei das erste Byte um 64 vergrößert wurde, die anderen Bytes unverändert. Die dann folgenden Bytes sind der Inhalt der Anfrage. Beispiel eUp: bytes = \[2024, 98, 2, 140, 100, 0, 0, 0, 0\]. Die 100 wären der Rohwert des SoC. In Prozent umgerechnet wäre beim eUp eine Division durch 2,5. Um auf den angezeigten SoC zu kommen, ist noch etwas Umrechnung erforderich, da der obere und untere Bereich des Akkus als Reserve vorgehalten wird:

    self.soc = round(bytes[4]/2.5*51/46-6.4)

#### calcODO(self, bytes)
berechnet den Kilometerstand aus Rohwerten analog zum schon beschriebenen SoC und speichert ihn in der Klassenvariable odo. Auch diese Umrechnung ist fahrzeugtyp-indiviuell. Es ist eine Standard-PID für das Motorsteuergerät definiert (1,166), diese wird aber nicht von allen Fahrzeugen unterstützt. eUp, eGolf unterstützen sie nicht, Passat GTE hingegen schon

[zurück](#inhalt)

## chargepoints.py
chargepoints.py definiert die Ladepunktklasse. In dieser sind Variablen und Funktionen, die den Ladepunkt betreffen.

### Variablen
1. **chargepointId** - Nummer des Ladepunktes
2. **plugstate** - Zustand des Ladesteckers des Ladepunktes (gesteckt oder nicht gesteckt)
3. **counterAtPlugin** - Zählerstand des Energiezählers des Ladepunktes beim Stecken des Stecker
4. **counter** - aktuellster Zählerstand des Energiezählers
5. **connectecId** - aktuell am Ladepunkt gewähltes Fahrzeug (manuell oder per RFID)

### Hilfsfunktionen
1. **getCounterTopic(self)** - gibt das Topic für den Zählerstand des Ladepunktes zurück
2. **getPlugStateTopic(self)** - gibt das Topic für den Zustand des Steckers des Ladepunktes zurück
3. **getConnectedIdTopic(self)** - gibt das Topic zurück, in dem die ID des mit dem Ladepunkt verbundenen Fahrzeugs zu finden ist

### Call-Back-Funktionen
1. **cb_energycounter(self, client, userdata, msg)** - Immer wenn eine neue Botschaft mit aktuellem Zählerstand eintrifft, wird dieser in dieser Funktion in der Klassenvariable counter abgelegt.
2. **cb_connectedVehicle(self, client, userdata, msg)** - Diese Funktion wird aufgerufen, wenn das Topic mit der ID des verbundenen Fahrzeugs beschrieben wird. Die ID wird in der Klassenvariable connectedId gespeichert.
3. **cb_plug(self, client, userdata, msg)** - Diese Funktion wird aufgerufen, wenn das Topic mit dem Steckerzustand des Ladepunktes beschrieben wird. Der Steckerzustand wird in der Klassenvariable plugstate gespeichert. Wechselt der Zustand des Steckers von ungesteckt nach gesteckt, wird der Wert des Energiezählers ind der Klassenvariable counterAtPlugin gespeichert. Wechselt der Zustand des Steckers von gesteckt auf ungesteckt, passieren etliche Dinge: Zunächst wird mittels counter und counteAtPlugin die geladene Energiemenge berechnet. Dann wird aus der konfigurierten Fahrzeugliste (configuration.py) das Fahrzeug identifiziert, das an den Ladepunkt angesteckt ist. Zusammen mit dem aktuellen Datum wird ein Eintrag in das lokale Ladelog geschrieben. Ist für das gefundene Fahrzeug die Nutzung von Spritmonitor definiert, wird dieser erzeugt.

[zurück](#inhalt)

## energylog.py

## spritmonitor.py

## startAtBoot.sh

## Erweiterung um neue Fahrzeugtypen
