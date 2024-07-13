# Funktion und Aufbau von soc_Helper; Erweiterung der bekannten Fahrzeuge
In diesem Dokument wird der Aufbau von soc_helper im Detail beschrieben. Am Ende befindet sich eine Anleitung, wie weitere Fahrzeugtypen ergänzt werden können.

## Inhalt

1. [Ablauf eines Ladevorgangs](#ablauf-eines-ladevorgangs)
1. [soc_helper - das Hauptprogramm](#soc_helperpy)
1. [cars.py - Fahrzeugspezifischer Code, Fahrzeugtypenklassen](#carspy)
1. [chargepoints.py - Ladepunktspezifischer Code](#chargepointspy)
1. [energylog.py - Funktionalität zum lokalen Speichern der Ladevorgänge](#energylogpy)
1. [spritmonitor.py - Verbindungscode zur Spritmonitor-Anbindung](#spritmonitorpy)
1. [startAtBoot.sh - Skript, das in die Nutzer-Crontab eingetragen werden kann, um den soc_helper bei Start des Rechner mitzustarten](#startatbootsh)

## Ablauf eines Ladevorgangs
Für jedes definierte Fahrzeug und jeden Ladepunkt wird in der Datei configuration.py eine Instanz einer Fahrzeugklasse beziehungsweise einer Ladepunktklasse angelegt. Jede dieser Instanzen hat verschiedene Callback-Funktionen, die beim Eintreffen der von ihnen abbonierten MQTT-Topics aufgerufen werden.

1. Das Fahrzeug mit aktivem WiCAN nähert sich dem heimischen WLAN.
2. Der WiCAN bucht sich ins WLAN ein, verbindet sich mit dem MQTT-Broker der OpenWB und sendet sein "status": "online" an das Status-Topic des betreffenden Fahrzeugs
3. Die Statusmeldung wird vom soc_helper empfangen und die Callback-Funktion cb_status der Fahrzeugklasseninstanz wird aufgerufen. Da der Status "online" ist, werden die Abfragen nach SoC und Odometer über das Tx-Topic an den MQTT-Broker und damit den WiCAN verschickt, sofern die Request-ID ungleich 0 ist.
4. Der WiCAN im Fahrzeug schickt die Antworten auf die Anfragen an das Rx-Topic, sie werden vom soc_helper empfangen und die Callback-Funktion cb_rx der Fahrzeugklasseninstanz wird aufgerufen. Wenn eine SoC-Antwort erkannt wurd, wird die Umrechungsfunktion der Klasseninstanz aufgerufen und der berechnete SoC klasseninstanz-intern abgespeichert und an den zugehörigen Fahrzeugeintrag der OpenWB geschickt. Der Odometerwert wird vorerst nur in der Klasseninstanz abgespeichert.
5. Der WiCAN legt sich möglicherweise schlafen. Falls er durch Laden der NV-Batterie geweckt wird, finden die oben genannten Schritte erneut statt.
6. Die Callback_Funktion cb_plug aller Ladepunkte wird periodisch aufgerufen, da die zugehörige Botschaft fortwährend beschrieben wird. Das Stecken des Ladesteckers löst eine Zustandsänderung aus. In der betroffenen Ladepunktklasseninstanz wird der Steckerzustand plugstate mit True beschrieben und der Zählerstand des Ladestromzählers in counterAtPlugin gesichert.
7. Die Callback-Funktion cb_connectedVehicle wird periodisch aufgerufen und speichert die ID des in der OpenWB gewählte Fahrzeug des Ladepunktes in der Instanzvariable connectedId.
8. Die Callback-Funktion cb_energycounter wird periodisch aufgerufen und speichert den Zählerstand des Ladepunktes in der Instanzvariable counter.
9. Beim Lösen des Ladesteckers erkennt die Callback-Funktion cb_plug die Zustandsänderung. Sie berechnet die geladene Energiemenge, ermittelt die Fahrzeugklasseninstanz des an den Ladpunkt angeschlossene Fahrzeugs, speichert das Datum, wandelt es in einen String für das Logging um, speichert den Ladevorgang lokal und erzeugt wenn gewünscht einen Eintrag bei Spritmonitor.

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

Darüber hinaus hat die Fahrzeug-Grundklasse folgende Variablen, die nicht bei der Konfiguration gesetzt werden sollten
1. **odo** - Letzter vom Fahrzeug empfangener Kilometerstand
1. **soc** - Letzter vom Fahrzeug emfangener SoC
1. **openwbsoc** - Letzter von der OpenWB empfanegener berechneter SoC

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

#### cb_status(self, client, userdata, msg)
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
berechnet den Kilometerstand aus Rohwerten analog zum schon beschriebenen SoC und speichert ihn in der Klassenvariable odo. Auch diese Umrechnung ist fahrzeugtyp-indiviuell. Es ist eine Standard-PID für das Motorsteuergerät definiert (1,166), diese wird aber nicht von allen Fahrzeugen unterstützt. eUp, eGolf unterstützen sie nicht, Passat GTE beispielsweise schon.

    self.odo = ( bytes[3]*16777216 + bytes[4]*65536 + bytes[5]*256 + bytes[6] )/10 # Standard-PID 166 vom MSG [2024, 65, 166, aa, bb, cc, dd, xx, xx]
    
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
3. **cb_plug(self, client, userdata, msg)** - Diese Funktion wird aufgerufen, wenn das Topic mit dem Steckerzustand des Ladepunktes beschrieben wird. Der Steckerzustand wird in der Klassenvariable plugstate gespeichert. Wechselt der Zustand des Steckers von ungesteckt nach gesteckt, wird der Wert des Energiezählers in der Klassenvariable counterAtPlugin gespeichert. Wechselt der Zustand des Steckers von gesteckt auf ungesteckt, passieren etliche Dinge: Zunächst wird mittels counter und counterAtPlugin die geladene Energiemenge berechnet. Dann wird aus der konfigurierten Fahrzeugliste (configuration.py) das Fahrzeug identifiziert, das an den Ladepunkt angesteckt ist. Zusammen mit dem aktuellen Datum wird ein Eintrag in das lokale Ladelog geschrieben. Ist für das gefundene Fahrzeug die Nutzung von Spritmonitor definiert, wird dieser erzeugt.

[zurück](#inhalt)

## energylog.py
ernergylog.py stellt die Funktionen für das schreiben des lokalen Ladelogs bereit.

### Funktionen
1. **init(path)** - Versucht, die lokale Ladelogdatei zu öffnen. Ist diese nicht vorhanden, wird sie neu angelegt und mit Spaltenüberschriften versehen. Der Filehandler savefile wird als globale Variable beschrieben.
2. **write(line)** - schreibt einen Ladevorgang (String line) in die Datei mit dem Handle savefile und schreibt den Buffer auf die lokale Platte.

[zurück](#inhalt)

## spritmonitor.py
Die Datei ist das Interface zu spritmonitor.de. Sie enthält Funktionen zum Verbinden mit Spritmonitor, zum Auslesen des letzten gespeicherten Beldaungsvorgangs und zum Anlegen enes neuen Eintrags. Die Funktionen sind nahezu unverändert aus dem [spritmonitor-Beispielcode](https://github.com/FundF/Spritmonitor-API-sample-code) übernommen.

[zurück](#inhalt)

## startAtBoot.sh
Um den soc_helper beim Booten eines Linux-Rechners mit zu starten, kann man einen Eintrag in der crontab des Benutzers anlegen.  Näheres dazu steht in der Datei. Der Eintrag in der crontab startet dieses Shellskript, was wiederum den soc_helper startet.

[zurück](#inhalt)

## Erweiterung um neue Fahrzeugtypen
Sofern die OBD2-Anfragen und Antworten bekannt sind, läßt sich der soc_helper einfach um neue Fahrzeugtypen erweitern. Folgende Schritte sind dafür nötig:

1. Datei cars.py öffnen
2. Abschnitt einer Fahrzeugtypenklasse (z.B. class eUp(carclass)) kopieren.
3. Die neue Klasse umbenennen, also eUp ersetzen durch eine kurze und eingängige Beschreibung des neuen Fahrzeugtyps
4. die SOC_REQ_ID, SOC_RESP_ID, SOC_REQ_DATA, ODO_REQ_ID, ODO_RESP_ID, ODO_REQ_DATA passen definieren. Die Zahlen sollten Ganzzahlen sein.
5. Wenn eine ID größer als 2047 ist, handelt es sich sicher um eine erweiterte 29-Bit-ID. In diesem Fall muß im zugehörigen String (SOC_REQUEST und/oder ODO_REQUEST) hinter dem "extd": true stehen, ansonsten false.
6. Die Umrechnungsfunktionen für soc und odo müssen vermutlich dem Fahrzeug angepaßt werden. Wenn in der Quelle der OBD-Informationen nichts angegeben ist, muß durch Vergleich der Rohwerte mit den im Fahrzeug angezeigten SoC-Werten oder dem Kilometerstand eine Formel ermittelt werden. Beispielsweise sei 100% SOC mit einem Rohwert von 240 in Listenelement 4 und 10% SOC mit einem Rohwert von 40 verbunden. Eine Ausgleichsgerade würde eine Steigung von (100%-10%)/(240-40)=0,45 ergeben. Um von 10% auf 0% zu kommen, sind (10%-0%)/0,45=22,222 Rohwerte erforderlich, also 40-22,222=17,778 Rohwerte Offset. Die Formel für das Beispiel lautet daher: self.soc = (bytes[4]-17,7)*0,45
7. Wenn die Definition der neuen Fahrzeugtypklasse funktioniert, bitte unbedingt als Pull Request oder den Codeschnippsel per Nachricht an mich zustellen.

### Hilfe zur Ermittlung der IDs und Daten

[zurück](#inhalt)
