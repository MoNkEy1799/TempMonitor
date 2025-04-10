from sql import SQLDatabase, ESP_DEVICES
import sys
import re
from datetime import datetime, timedelta

def format_text(s: str, bold: bool = False, underline: bool = False) -> str:
    e = ""
    if bold:
        e += "\033[1m"
    if underline:
        e += "\033[4m"
    return f"{e}{s}\033[0m"

if len(sys.argv) < 2:
    print(f"Prints out entries from the SQL database. Usage:\n\n"
          f"\t{format_text('-d', bold=True)} {format_text('dev', underline=True)}\n"
          f"\t\tThe esp devices you want to print out. Separated by commas. If no devices are given, all esp devices are searched.\n"
          f"\t{format_text('-n', bold=True)} {format_text('num', underline=True)}\n"
          f"\t\tPrint the last n entries from the SQL database. Possible values are 1-1200.\n"
          f"\t{format_text('-h', bold=True)} {format_text('hour', underline=True)}\n"
          f"\t\tPrint the last h hours from the SQL database. Possible values are 1-16.\n"
          f"\t{format_text('-m', bold=True)} {format_text('minute', underline=True)}\n"
          f"\t\tPrint the last m minutes from the SQL database. Possible values are 1-1200.\n"
          f"\t{format_text('-t', bold=True)} {format_text('time', underline=True)}\n"
          f"\t\tPrint all entries up to time t (of the current day). This has to be combined with either -n, -h or -m. Format: H:M in 24h format (zero padding not necessary).")
    exit(1)

ESP, N, TIME_H, TIME_M, H, M = [None for _ in range(6)]
argv = sys.argv[1:]

try:
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ["-dev", "-d"]:
            ESP = list()
            for dev in re.sub(r"\s+", "", argv[i+1]).split(","):
                if not re.search("^(esp[1-8]|[1-8])$", dev):
                    print("Please provide a valid esp device: esp[1-8] ('esp' is optional)"); exit(1)
                dev = f"esp{int(dev.strip('esp'))}"
                ESP.append(dev) if dev not in ESP else 0
            i += 1
        elif arg in ["-num", "-n"]:
            if not re.search("[1-9]+", argv[i+1]) or int(argv[i+1]) > 1000:
                print("Please provide a valid number of entries (< 1000)"); exit(1)
            if H or M:
                print("Can only use one of these options: -n -hour -minute!"); exit(1)
            N = int(argv[i+1])
            i += 1
        elif arg in ["-time", "-t"]:
            if not re.search("([01]?[0-9]|2[0-3]):([0-5]?[0-9])", argv[i+1]):
                print("Please provide a valid time, format: H:M (24h format with or without zero padding)"); exit(1)
            TIME_H, TIME_M = [int(s) for s in argv[i+1].split(":")]
            i += 1
        elif arg in ["-hour", "-h"]:
            if not re.search("[1-9]+", argv[i+1]) or int(argv[i+1]) > 16:
                print("Please provide a valid number of hours (< 16)"); exit(1)
            if N or M:
                print("Can only use one of these options: -n -hour -minute!"); exit(1)
            H = int(argv[i+1])
            i += 1
        elif arg in ["-minute", "-m"]:
            if not re.search("[1-9]+", argv[i+1]) or int(argv[i+1]) > 1000:
                print("Please provide a valid number of minutes (< 1000)"); exit(1)
            if N or H:
                print("Can only use one of these options: -n -hour -minute!"); exit(1)
            M = int(argv[i+1])
            i += 1
        else:
            print(f"Unknown option: {arg}"); exit(1)
        i += 1
except IndexError:
    print(f"Please provide a value for {argv[i]}"); exit(1)

N = N if N else H * 60 if H else M
if TIME_H and not N:
    print("Cannot use -time without -n!"); exit(1)
if not ESP:
    ESP = ESP_DEVICES

sql = SQLDatabase()
for dev in ESP:
    if N:
        if TIME_H:
            time = datetime.now().replace(hour=TIME_H, minute=TIME_M, second=0, microsecond=0)
            sql.cursor.execute(f"SELECT rowid FROM {dev} WHERE timestamp BETWEEN ? and ?", (time, time+timedelta(minutes=1)))
            try:
                max_id = sql.cursor.fetchall()[0][0]
            except IndexError:
                print(f"Time: {time} is not in the SQL database for dev: {dev}. Please use another time")
                continue
            sql.cursor.execute(f"SELECT * FROM {dev} WHERE rowid BETWEEN {max_id - N + 1} and {max_id}")
        else:
            sql.cursor.execute(f"SELECT MAX(rowid) FROM {dev}")
            max_id = sql.cursor.fetchall()[0][0]
            if max_id is None:
                print(f"\n### SQL ERROR: Could not get max_id for table/ device: {dev} ###")
                continue
            sql.cursor.execute(f"SELECT * FROM {dev} WHERE rowid > {max_id - N}")

    fetch = sql.cursor.fetchall()
    print(f"\n{dev}:")
    if dev in ESP_DEVICES:
        print(f"{'timestamp':<24}{'temperature':<15}{'pressure':<15}{'humidity':<15}light")
        for row in fetch:
            time, t, p, h, l = row
            print(f"{time:<24}{t:<15}{p:<15}{h:<15}{l}")