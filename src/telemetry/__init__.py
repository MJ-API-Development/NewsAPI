import time
from functools import wraps
from pydantic import BaseModel, Field


class TimeMetrics(BaseModel):
    """
        **TimeMetrics**
        this model is used to send time metrics
    """

    method_name: str = Field()
    latency: float = Field(default=0)

    class Config:
        title = "Financial News Parser Time Metrics Data"

    def update_latency(self, name: str, latency: float):
        self.method_name = name
        self.latency = latency


class ErrorMetrics(BaseModel):
    method_name: str = Field()
    error_name: str = Field()


class Telemetry(BaseModel):
    """
    **Telemetry**
        this model is used to send telemetry data
        to the admin about this microservice
    """
    timing_data: list[TimeMetrics] = Field(default_factory=list())
    errors: list[ErrorMetrics] = Field(default_factory=list())

    class Config:
        title = "Financial News Parser Telemetry Data"

    async def add_error_metric(self, error_metric: ErrorMetrics):
        self.errors.append(error_metric)

    async def add_timing_data(self, timing_data: TimeMetrics):
        self.timing_data.append(timing_data)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def timing_count(self) -> int:
        return len(self.timing_data)

    async def return_data_point(self) -> dict:
        """
        Returns the telemetry data as a dictionary
        """
        return dict(
            timing_data=[timing.dict() for timing in self.timing_data],
            timing_count=self.timing_count,
            errors=[_error.dict() for _error in self.errors],
            error_count=self.error_count)


class TelemetryStream:
    """
    Telemetry stream that captures telemetry data for a specified duration
    """

    def __init__(self, duration: int = 60):
        self.duration = duration
        self.telemetry_data: dict[int, Telemetry] = {}

    async def capture_error(self, method_name: str, error_type: str):
        """
        Handler to capture error telemetry
        """
        current_minute: int = int(time.time() / 60)
        error_metric = ErrorMetrics(method_name=method_name, error_type=error_type)
        await self.telemetry_data[current_minute].add_error_metric(error_metric=error_metric)

    async def return_data_stream(self) -> tuple[time, dict[str, int | list[dict[str, str | int]]]]:
        for _time, data in self.telemetry_data.items():
            yield _time, data.return_data_point()


def capture_latency(name: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_minute = int(time.time() / 60)
            start_time = time.monotonic()
            # TODO add try exceot Clauses for all error types then capture the data on the telemtry stream
            result = await func(*args, **kwargs)
            end_time = time.monotonic()
            duration = end_time - start_time
            telemetry = TimeMetrics(method_name=name, latency=duration)

            await telemetry_stream.telemetry_data[current_minute].add_timing_data(timing_data=telemetry)
            return result

        return wrapper

    return decorator


telemetry_stream = TelemetryStream()
