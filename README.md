# soc_helper

## Vorweg
Falls nur der SoC des Fahrzeugs vom WiCAN zu einem MQTT-Broker übertragen werden soll, kann der WiCAN inzwischen alleine verwendet werden. Ab Firmware 3.30 erfolgt eine starke Weiterentwicklung in diese Richtung. Auch andere Werte wie Reichweite, Kilometerstand können bei einigen Fahrzeugen schon direkt per MQTT übertragen werden. Ein Einstieg findet sich unter (https://forum.openwb.de/viewtopic.php?t=9397). Der soc_helper bietet darüber hinausgehend nur die Anbindung an Spritmonitor und Beispiel für eigenen Code.

## Motivation

Der soc_helper ist aus einem persönlichen Bedürfnis entstanden: Vorhanden sind eine [OpenWB](https://openwb.de/main/) und ein eUp. Im ersten Jahr gibt es gratis weConnect zum Auto dazu. Solange dieser Zugang besteht, kann die OpenWB den Ladezustand automatisch von einem VW-Server abfragen. Dies ist nützlich, um die Ladung akkuschonend bei 80% zu beenden.

Der Online-Zugang erwies sich für mich nicht als besonders stabil, und auch die Vorklimatisierung per App hat meistens kommentarlos nicht funktioniert. Ich wollte das Auslesen des SoC selber in die Hand nehmen und dabei etwas Python lernen.

Mittlerweile funktioniert der soc_helper, und ganz reibungslos werden der Ladezustand an die Wallbox übertragen und bei Spritmonitor mein Ladelog geführt.

## Funktion
soc_helper ist ein Vermittler zwischen OpenWB und Fahrzeug. Damit das funktioniert, muß ein [Meatpi WiCAN](https://github.com/meatpiHQ/wican-fw) in der OBD-Buchse des Fahrzeugs stecken. Dieser OBD-Dongle bucht sich ins heimische WLAN ein, sobald dies verfügbar ist und meldet sich am MQTT-Broker der OpenWB an.

soc_helper reagiert auf das Anmelden und fragt via MQTT Ladezustand der Batterie sowie Kilometerstand ab. Anschließend wird der Ladezustand in das manuelle SoC-Modul der Wallbox geschrieben. Der WiCAN legt sich nach kurzer Zeit stromsparend schlafen.

Beim Abziehen des Ladesteckers aus dem Auto protokolliert der soc_helper den Kilometerstand, den Start-SoC und den berechneten End-SoC in einer lokalen Datei. Es ist möglich, den Ladevorgang bei [Spritmonitor.de](https://spritmonitor.de) automatisch zu protokollieren. Dazu holt sich soc_helper den letzten Kilometerstand ab und übermittelt neuen Kilometerstand, gefahrene Strecke, Ladungsmenge und End-SOC. Es können ein Default-Strompreis sowie verschiedene vorher definierte Attribute mit übermittelt werden.

## Unterstützte Fahrzeuge

### Funktioniert:
1. eUp
2. VW MEB (ID3, ID4 und abgeleitete Varianten von Skoda,Seat)
3. Standard-Abfragen für Verbrenner sofern unterstützt: Tankfüllstand (als SOC an die Wallbox), Kilometerstand
4. eGolf
5. Renault Zoe alt (PH1)

### Vorbereitet (Tester gesucht):
1. Ora Funky Cat
2. Renault Zoe neu (PH2), nur SoC
3. Fiat 500e

Generell werden immer Tester gesucht. Ich freue mich über Rückmeldungen - entweder über das [OpenWB-Forum](https://forum.openwb.de/viewtopic.php?t=7451) oder per EMail an soc_helper\<at\>vortagsmett\<Punkt\>de.

## Dokumentation

Die Dokumentation der Erstinstallation befindet sich im Unterordner `Doku`: [Doku/Inbetriebnahme_soc_helper.md](Doku/Inbetriebnahme_soc_helper.md).

Du möchtest Dein bisher nicht unterstütztes Auto hinzufügen? [Doku/InternaUndErweiterung.md](Doku/InternaUndErweiterung.md)

Hilfreiche Links finden sich in [Doku/HilfreicheLinks.md](Doku/HilfreicheLinks.md).
