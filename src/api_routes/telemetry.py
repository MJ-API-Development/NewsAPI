from fastapi import APIRouter, Request

from telemetry import telemetry_stream

telemetry_router = APIRouter()

# This allows to stream telemetry data
data_stream = telemetry_stream.return_data_stream()


# noinspection PyUnusedLocal
@telemetry_router.api_route(path='/_admin/telemetry', methods=['GET'], include_in_schema=True)
def gather_telemetry(request: Request):
    """
    **gather_telemetry**
       **find a way to monitor the api then send the data over this API
    :param request:
    :return:
    """
    return next(data_stream)
