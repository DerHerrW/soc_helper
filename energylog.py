"""
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

import logging
from os.path import exists

def init(path):
    global savefile
    # lokale Ladedatei öffnen
    try:
        if not exists(path):
            logging.info(f'{path} existiert nicht. Lege neu an.')
            savefile = open(path,'a')
            savefile.write('Datum, Fahrzeugname, Kilometerstand, Energiemenge, Start-SOC (Auto), End-SOC (Wallbox)\n')
            savefile.flush()
        else:
            logging.info(f'Öffne existierende Logdatei {path}.')
            savefile = open(path,'a')
    except Exception as e:
        logging.error(f'Konnte Ausgabedatei {path} nicht anlegen oder öffnen: {e}')
    
def write(line):
    global savefile
    try:
        savefile.write(line)
        savefile.flush()
    except Exception as e:
        logging.error(f'lokales Schreiben der Ladedaten fehlgeschlagen: {e}')

