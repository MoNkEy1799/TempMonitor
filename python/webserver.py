from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn
from sql import SQLDatabase, ESP_DEVICES
from datetime import datetime, timedelta
from asyncio import Lock
import logging

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,  # Enable existing loggers (including uvicorn)
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(levelname)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },
    'handlers': {
        'default': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'stream': 'ext://sys.stdout',  # Use stdout for stream logs
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'standard',
            'filename': 'app.log',
            'maxBytes': 1024 * 1024 * 1,  # 1MB file size limit
            'backupCount': 3,
        },
    },
    'loggers': {
        'uvicorn': {
            'level': 'INFO',
            'handlers': ['default', 'file'],
            'propagate': False,
        },
        'uvicorn.access': {
            'level': 'INFO',
            'handlers': ['default'],
            'propagate': False,
        },
        'uvicorn.error': {
            'level': 'INFO',
            'handlers': ['default'],
            'propagate': False,
        },
    },
}
rpi_logger = logging.getLogger(__name__)

mainPath = "/home/rpi_user/path_to_repo"
app = FastAPI()
app.mount("/static", StaticFiles(directory=f"{mainPath}/webserver/static"))
templates = Jinja2Templates(directory=f"{mainPath}/webserver/templates")
sqlDB = SQLDatabase()
cacheLock = Lock()
cache = {
    "temperature":
        {6: {"response": None, "time": None},
        24: {"response": None, "time": None},
        72: {"response": None, "time": None},
        168: {"response": None, "time": None},},
    "pressure":
        {6: {"response": None, "time": None},
        24: {"response": None, "time": None},
        72: {"response": None, "time": None},
        168: {"response": None, "time": None},},
    "humidity":
        {6: {"response": None, "time": None},
        24: {"response": None, "time": None},
        72: {"response": None, "time": None},
        168: {"response": None, "time": None},},
    "light":
        {6: {"response": None, "time": None},
        24: {"response": None, "time": None},
        72: {"response": None, "time": None},
        168: {"response": None, "time": None},}
}

@app.get("/", response_class=HTMLResponse)
async def main(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("main.html", {"request": request})

@app.get("/data/{id}/{device}/{timePre}/{timePost}")
async def data(id: str, device: str, timePre: str, timePost: str) -> None:
    rpi_logger.info(f"Data request by {id} for {device} between {timePre} - {timePost}")
    pre = datetime(*[int(c) for c in timePre.split("-")], 0, 0, 0)
    post = datetime(*[int(c) for c in timePost.split("-")], 23, 59, 59)
    out = sqlDB.readData(pre, post, device)
    readings = "temperature, pressure, humidity and light"
    with open(f"{mainPath}/webserver/static/data/{id}.txt", "w") as file:
        file.write(f"# Data from device: {device}\n")
        file.write(f"# Data includes {readings} readings from {pre} to {post}\n")
        file.write(f"# To import the data to a pandas.DataFrame use the following code:\n")
        file.write(f"# import pandas as pd\n")
        file.write(f'# data = pd.read_csv("data.txt", sep="\s+", header=6)\n')
        file.write(f"# \n")
        if device in ESP_DEVICES:
            file.write(f"{'timestamp':<24}{'temperature':<15}{'pressure':<15}{'humidity':<15}light\n")
            for row in out:
                time, t, p, h, l = row
                file.write(f"{time:<24}{t:<15}{p:<15}{h:<15}{l}\n")

@app.get("/update/{plotType}")
async def update(plotType: str, request: Request) -> dict:
    if plotType not in ["temperature", "pressure", "humidity", "light"]:
        rpi_logger.warning(f"Requested plot type: {plotType} is not valid in `async def update`. IP: {request.client.host}")
        return {"ERROR": "Wrong plot type!"}
    
    try:
        out = sqlDB.getLastEntry(plotType)
    except Exception as e:
        rpi_logger.error(f"Exception when calling: update({plotType})")
        rpi_logger.error(e)
        return {}
    return {"xdata": [out[dev]["time"] for dev in ESP_DEVICES], "ydata": [out[dev]["value"] for dev in ESP_DEVICES]}
    
@app.get("/range/{plotType}/{duration}")
async def rangeUpdate(plotType: str, duration: str, request: Request) -> dict:
    if plotType not in ["temperature", "pressure", "humidity", "light"]:
        rpi_logger.warning(f"Requested plot type: {plotType} is not valid in `async def rangeUpdate`. IP: {request.client.host}")
        return {"ERROR": "Wrong plot type!"}
    if int(duration) > 200:
        rpi_logger.warning(f"Requested duration above 200h: {duration}. IP: {request.client.host}")
        return {"ERROR": "Durations above 200h are not allowed!"}

    # duration * 3.6 = update every x seconds
    # but for dur = 6h still update every 60s, since this is the rate of the data collection
    validTime = max([60, int(int(duration) * 3.6)])
    datePost = (datetime.now() + timedelta(minutes=1)).replace(microsecond=0, second=0)
    datePre = datePost - timedelta(hours=int(duration), minutes=1)
    async with cacheLock:
        cacheTime = cache[plotType][int(duration)]["time"]
        if cacheTime and datePost - cacheTime < timedelta(seconds=validTime):
            rpi_logger.info(f"Sending cached response: plot: {plotType}, duration: {duration}.")
            return cache[plotType][int(duration)]["response"]
    try:
        out = sqlDB.getRange(datePre, datePost, plotType, duration=int(duration))
    except Exception as e:
        rpi_logger.error(f"Exception when calling: rangeUpdate({plotType}, {duration})")
        rpi_logger.error(e)
        return {}
    response = {"xdata": [out[dev]["time"] for dev in ESP_DEVICES], "ydata": [out[dev]["value"] for dev in ESP_DEVICES]}
    async with cacheLock:
        cache[plotType][int(duration)]["time"] = datePost
        cache[plotType][int(duration)]["response"] = response
    
    return JSONResponse(content=response, headers={"Cache-Control": f"max-age={validTime}, public"})
    
def startWebserver(app):
    uvicorn.run(app, host="0.0.0.0", port=80, log_config=LOGGING_CONFIG, access_log=False)

if __name__ == "__main__":
    startWebserver(app)
