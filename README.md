# soc_helper
Der soc_helper ist aus einem persönlichen Bedürfnis entstanden: Vorhanden sind eine [OpenWB](https://openwb.de/main/) und ein eUp. Im ersten Jahr gibt es gratis weConnect zum Auto dazu. Solange dieser Zugang besteht, kann die OpenWB den Ladezustand automatisch von einem VW-Server abfragen. Dies ist nützlich, um die Ladung akkuschonend bei 80% zu beenden. Der Online-Zugang erwies sich für mich nicht als besonders stabil, und auch die Vorklimatisierung per App hat meistens kommentarlos nicht funktioniert. Ich wollte die Dinge also selber in die Hand nehmen und dabei etwas Python lernen.

## Funktion
soc_helper ist ein Vermittler zwischen OpenWB und Fahrzeug. Damit das funktioniert, muß ein (Meatpi WiCAN)[https://github.com/meatpiHQ/wican-fw]in der OBD-Buchse des Fahrzeugs stecken. Dieser OBD-Dongle bucht sich ins heimische WLAN ein, sobald dies verfügbar ist und meldet sich am MQTT-Broker der OpenWB an. soc_helper reagiert auf das Anmelden und fragt via MQTT Ladezustand der Batterie sowie Kilometerstand ab. Anschließend wird der Ladezustand in das manuelle SoC-Modul der Wallbox geschrieben. Der WiCAN legt sich nach kurzer Zeit stromsparend schlafen.
Beim Abziehen des Ladesteckers aus dem Auto protokolliert der soc_helper den Kilometerstand, den Start-SoC und den berechneten End-SoC in einer lokalen Datei. Es ist möglich, den Ladevorgang bei [Spritmonitor.de](https://spritmonitor.de) automatisch zu protokollieren. Dazu holt sich soc_helper den letzten Kilometerstand ab und übermittelt neuen Kilometerstand, gefahrene Strecke, Ladungsmenge und End-SOC. Es können ein Default-Strompreis sowie verschiedene vorher definierte Attribute mit übermittelt werden.

## Dokumentation

Die Dokumentation der Erstinstallation befindet sich im Unterordner `Doku`: [Erstinstallation](Doku/Inbetriebnahme_soc_helper.md).

Hilfreiche Links finden sich in [Doku/HilfreicheLinks.md]

## Hilfreiche Links

1. [wican-Firmware](https://github.com/meatpiHQ/wican-fw/releases/)
1. [Dokumentation und Quellcode des WiCAN](https://github.com/meatpiHQ/wican-fw)
1. [Bestellung WiCAN](https://eu.mouser.com/c/?m=MeatPi)
1. [CAN-Datenbank VW](https://www.goingelectric.de/wiki/Liste-der-OBD2-Codes/)
1. [Übersicht Ptorokoll CAN-TP](https://en.m.wikipedia.org/wiki/ISO_15765-2)
1. [MQTT-Explorer](http://mqtt-explorer.com/)
1. [Installation von Python-Paketen](https://u-labs.de/portal/was-ist-eine-python-virtualenv-venv-und-wozu-braucht-man-sie-virtuelle-python-umgebung-fuer-einsteiger/)
1. [API von Spritmonitor](https://api.spritmonitor.de/doc)
1. [Nutzungsbeispiele der API](https://github.com/FundF/Spritmonitor-API-sample-code)
1. [Kia/ Hyundai: evDash](https://github.com/nickn17/evDash)
1. [MEB-OBD2-IDs](https://github.com/spot2000/Volkswagen-MEB-EV-CAN-parameters/blob/main/VW%20MEB%20UDS%20PIDs%20list.csv)
1. [WiCAN Issue-Tracker](https://github.com/meatpiHQ/wican-fw/issues)
1. [SOC/Odo Fiat500e](https://github.com/meatpiHQ/wican-fw/issues/95)
1. [Übersicht CAN / Diagnoseprotokoll](http://www.emotive.de/documents/WebcastsProtected/Transport-Diagnoseprotokolle.pdf)
1. [Mehr OBD2-PIDs](https://github.com/iternio/ev-obd-pids/blob/main/)
1. [UDS Faltposter](https://automotive.softing.com/fileadmin/sof-files/pdf/de/ae/poster/UDS_Faltposter_softing2016.pdf)
1. [Doku ELM327-Chip (incl AT-Kommandos)](https://www.elmelectronics.com/DSheets/ELM327DSH.pdf)
