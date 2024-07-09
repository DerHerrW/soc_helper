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

