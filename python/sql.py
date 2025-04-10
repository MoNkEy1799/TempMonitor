from datetime import datetime, timedelta
from sqlite3 import Connection as SQLite3Connection, OperationalError
import numpy as np

ESP_DEVICES = [f"esp{i}" for i in range(1, 9)]

SQL_DB_PATH = ""

class SQLDatabase:
    def __init__(self, loc: str = SQL_DB_PATH, mode: str="ro") -> None:
        try:
            self.connection = SQLite3Connection(f"file:{loc}?mode={mode}")
        except OperationalError:
            self.connection = SQLite3Connection(loc)
        self.cursor = self.connection.cursor()
        self._createTables()
        
    def _createTables(self) -> None:
        cmd = """
        CREATE TABLE IF NOT EXISTS {}
        (
            timestamp TEXT PRIMARY KEY,
            temperature REAL NOT NULL,
            pressure REAL NOT NULL,
            humidity REAL NOT NULL,
            light REAL NOT NULL
        );
        """
        for dev in ESP_DEVICES:
            self.cursor.execute(cmd.format(dev))

    def _reduceData(self, fetchResult: list[tuple], maxLength: int=1000) -> tuple[list]:
        if len(fetchResult) > maxLength:
            time, value = list(), list()
            indices = np.round(np.linspace(0, len(fetchResult) - 1, maxLength)).astype(int)
            for i in indices:
                time.append(fetchResult[i][0])
                value.append(fetchResult[i][1])
            return time, value
        return zip(*fetchResult)
        
    def insertData(self, dev: str, date: datetime, t: float, p: float, h: float, l: float) -> None:
        cmd = """INSERT INTO {} (timestamp, temperature, pressure, humidity, light) VALUES (?, ?, ?, ?, ?);"""
        self.cursor.execute(cmd.format(dev), (date, t, p, h, l))
        self.connection.commit()

    def readData(self, timeFrom: datetime, timeTo: datetime, dev: str) -> list[tuple]:
        cmd = "SELECT * FROM {} WHERE timestamp BETWEEN ? AND ?"
        self.cursor.execute(cmd.format(dev), (timeFrom, timeTo))
        return self.cursor.fetchall()
    
    def getRange(self, timeFrom: datetime, timeTo: datetime, plotType: str, duration: int|None = None) -> dict:
        cmd = "SELECT timestamp, {} FROM {} WHERE timestamp BETWEEN ? and ?"
        result = dict()
        for dev in ESP_DEVICES:
            self.cursor.execute(cmd.format(plotType, dev), (timeFrom, timeTo))
            fetchResult = self.cursor.fetchall()
            if duration is not None:
                if len(fetchResult) < duration * 60:
                    current = timeTo.replace(second=0)
                    end = timeFrom.replace(second=0)
                    index = -1
                    while current > end:
                        if abs(index) > len(fetchResult):
                            fetchResult.insert(0, (str(current), None))
                        elif fetchResult[index][0][:16] < str(current)[:16]:
                            fetchResult.insert(len(fetchResult)+index+1, (str(current), None))
                        elif fetchResult[index][0][:16] > str(current)[:16]:
                            fetchResult.insert(len(fetchResult)+index, (str(current), None))
                            index -= 1
                        current -= timedelta(minutes=1)
                        index -= 1
            del fetchResult[:len(fetchResult) - duration * 60]
            time, value = self._reduceData(fetchResult)
            result[dev] = {"time": time, "value": value}
        return result
    
    def getLastEntry(self, plotType: str) -> dict:
        result = dict()
        cmd = "SELECT timestamp, {} FROM {} WHERE rowid IS {}"
        now = datetime.now().replace(microsecond=0, second=0)
        for dev in ESP_DEVICES:
            self.cursor.execute(f"SELECT MAX(rowid) FROM {dev}")
            max_id = self.cursor.fetchall()[0][0]
            self.cursor.execute(cmd.format(plotType, dev, max_id))
            time, value = self.cursor.fetchall()[0]
            if now - datetime.strptime(time, "%Y-%m-%d %H:%M:%S") > timedelta(minutes=2):
                time, value = str(now), None
            result[dev] = {"time": time, "value": value}
        return result
    