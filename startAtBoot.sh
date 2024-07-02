#!/bin/bash
#
# Dieses skript dient dazu, bei einem Aufruf beim booten durch cron den soc_helper zu starten. Dazu
# muss folgender Eintrag mit dem Befehl "crontab -e" als einzelne Zeile in die crontab des Nutzers
# eingetragen werden (am besten ans Ende):
#
# @reboot . $HOME/.profile; $HOME/soc_helper/startAtBoot.sh
#
# Bitte auch prüfen, ob für den Besitzer das Executable-Bit gesetzt ist. Wenn nicht, "chmod 755 startAtBoot.sh"
# ausführen.

sleep 10        # Warten, bis hoffentlich das Netz verfügbar ist
nohup $PWD/soc_helper/soc_helper.py >> $PWD/soc_helper/nohup.out 2>&1 & # soc_helper in den Hintergrund starten
