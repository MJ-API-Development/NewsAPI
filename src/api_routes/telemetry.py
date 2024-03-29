from fastapi import APIRouter, Request

from src.telemetry import telemetry_stream
from src.utils.my_logger import AppLogger

telemetry_router = APIRouter()

# This allows to stream telemetry data
data_stream = telemetry_stream.return_data_stream()


def log_file_reader() -> str:
    with open(AppLogger.logging_file) as file:
        for line in file.readlines():
            yield line


logfile_generator = log_file_reader()


# noinspection PyUnusedLocal
@telemetry_router.api_route(path='/_admin/telemetry/stream', methods=['GET'], include_in_schema=True)
async def gather_telemetry(request: Request):
    """
    **gather_telemetry**
       **find a way to monitor the api then send the data over this API
    :param request:
    :return:
    """
    async for data in data_stream:
        return data
    return dict(message="Data Stream Empty")


@telemetry_router.api_route(path='/_admin/telemetry/stats', methods=['GET'], include_in_schema=True)
async def gather_telemetry(request: Request):
    """
    **gather_telemetry**
       **find a way to monitor the api then send the data over this API
    :param request:
    :return:
    """
    return telemetry_stream.dict()


@telemetry_router.api_route(path='/_admin/telemetry/stream-logs', methods=['GET'], include_in_schema=True)
async def gather_telemetry(request: Request):
    """
    **gather_telemetry**
       **find a way to monitor the api then send the data over this API
    :param request:
    :return:
    """
    for log in logfile_generator:
        return log
    return {"message": "log file exhausted"}
