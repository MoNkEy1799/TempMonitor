from datetime import datetime, timedelta
from sql import SQLDatabase, ESP_DEVICES
from pathlib import Path

mainPath = "/home/rpi_user/path_to_repo"

def getDateRange(year: None | int=None, month: None | int=None) -> tuple[datetime]:
    now = datetime.now() - timedelta(days=2)
    if year is not None and month is not None:
        now = now.replace(year=year, month=month)
    first = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last = first.replace(year=first.year+first.month//12, month=first.month%12+1, day=1, hour=23, minute=59, second=59) - timedelta(days=1)
    return first, last

def backupData(year: None | int=None, month: None | int=None) -> None:
    database = SQLDatabase()
    first, last = getDateRange(year=year, month=month)
    for dev in ESP_DEVICES:
        res = database.readData(first, last, dev)
        Path(f"{mainPath}/backups/{first.year}/{first.month:0>2}").mkdir(parents=True, exist_ok=True)
        readings = "temperature, pressure, humidity and light"
        with open(f"{mainPath}/python/backups/{first.year}/{first.month:0>2}/{dev}.txt", "w") as file:
            file.write(f"# Data from device: {dev}\n")
            file.write(f"# Data includes {readings} readings from {first} to {last}\n")
            file.write(f"# To import the data to a pandas.DataFrame use the following code:\n")
            file.write(f"# import pandas as pd\n")
            file.write(f'# data = pd.read_csv("data.txt", sep="\s+", header=6)\n')
            file.write(f"# \n")
            if dev in ESP_DEVICES:
                file.write(f"{'timestamp':<24}{'temperature':<15}{'pressure':<15}{'humidity':<15}light\n")
                for row in res:
                    time, t, p, h, l = row
                    file.write(f"{time:<24}{t:<15}{p:<15}{h:<15}{l}\n")

def removeOldDownloads():
    dataFolder = Path(f"{mainPath}/webserver/static/data")
    for filePath in dataFolder.iterdir():
        filePath.unlink()

backupData()
removeOldDownloads()
