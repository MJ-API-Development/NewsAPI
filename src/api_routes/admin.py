from fastapi import APIRouter, Request

admin_router = APIRouter()


# noinspection PyUnusedLocal
@admin_router.api_route(path='/_admin/admin', methods=['GET'], include_in_schema=True)
def admin(request: Request):
    """
       **admin**
        will allow management tasks such as
            starting
            stopping
            restarting
            scheduling
            cancelling schedules
    :param request:
    :return:
    """
    pass
