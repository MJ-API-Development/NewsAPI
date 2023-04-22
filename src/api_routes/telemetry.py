from fastapi import APIRouter, Request

telemetry_router = APIRouter()


# noinspection PyUnusedLocal
@telemetry_router.api_route(path='/_admin/telemetry', methods=['GET'], include_in_schema=True)
def gather_telemetry(request: Request):
    """
       **find a way to monitor the api then send the data over this API
    :param request:
    :return:
    """
    pass
