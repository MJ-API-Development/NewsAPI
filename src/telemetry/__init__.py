import time
from functools import wraps
from pydantic import BaseModel, Field

from src.utils.my_logger import init_logger

telemetry_logger = init_logger('telemetry_logger')


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

    def __str__(self):
        return f"Method: {self.method_name} , Latency: {self.latency:.3f}"


class ErrorMetrics(BaseModel):
    method_name: str = Field()
    error_name: str = Field()


class Telemetry(BaseModel):
    """
    **Telemetry**
        this model is used to send telemetry data
        to the admin about this microservice
    """
    timing_data: list[TimeMetrics] = Field(default_factory=lambda: list())
    errors: list[ErrorMetrics] = Field(default_factory=lambda: list())

    class Config:
        title = "Financial News Parser Telemetry Data"

    async def add_error_metric(self, error_metric: ErrorMetrics):
        telemetry_logger.info(error_metric)
        self.errors.append(error_metric)

    async def add_timing_data(self, timing_data: TimeMetrics):
        telemetry_logger.info(timing_data)
        self.timing_data.append(timing_data)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def timing_count(self) -> int:
        return len(self.timing_data)

    @property
    def events_count(self) -> int:
        return self.error_count + self.timing_count

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
    Telemetry stream that captures telemetry data for a specified time_elapsed
    """

    def __init__(self):
        self.elapsed_time_minutes: int = 0
        self.method_names: set[str] = Field(default_factory=lambda: set())
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

    @property
    def highest_errors_per_minute(self) -> int:
        return max([telemetry.error_count for telemetry in self.telemetry_data.values()])

    @property
    def lowest_errors_per_minute(self) -> int:
        return min([telemetry.error_count for telemetry in self.telemetry_data.values()])

    @property
    def highest_latency_per_method(self) -> dict[str, float]:
        """
        **highest_latency_per_method**
            returns method names with their highest latency numbers
        :return:
        """
        method_max_latency = dict()
        for method in list(self.method_names):
            method_max_latency.update(
                method=max(*[lambda metric: metric.return_data_point().get('timing_data', {}).get('latency')
                             for metric in self.telemetry_data.values()]))
        return method_max_latency

    @property
    def lowest_latency_per_method(self) -> dict[str, float]:
        """
        **lowest_latency_per_method
            returns method names with their lowest latency numbers
        :return:
        """
        method_max_latency = dict()
        for method in list(self.method_names):
            method_max_latency.update(
                method=min(*[lambda metric: metric.return_data_point().get('timing_data', {}).get('latency')
                             for metric in self.telemetry_data.values()]))
        return method_max_latency

    def dict(self) -> dict[str, str | float | dict[str, float]]:
        """

        :return:
        """
        return dict(
            highest_errors_per_minute=self.highest_errors_per_minute,
            lowest_errors_per_minute=self.lowest_errors_per_minute,
            highest_latency_per_method=self.highest_latency_per_method,
            lowest_latency_per_method=self.lowest_latency_per_method)


def capture_latency(name: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_minute = int(time.time() / 60)
            start_time = time.monotonic()
            # TODO add try Except Clauses for all error types then capture the data on the telemetry stream
            result = await func(*args, **kwargs)
            time_metrics: TimeMetrics = TimeMetrics(method_name=name, latency=(time.monotonic() - start_time))

            if telemetry_stream.telemetry_data.get(current_minute, False):
                await telemetry_stream.telemetry_data[current_minute].add_timing_data(timing_data=time_metrics)
            else:
                telemetry = Telemetry()
                await telemetry.add_timing_data(timing_data=time_metrics)
                telemetry_stream.telemetry_data.update(current_minute=telemetry)
                telemetry_stream.elapsed_time_minutes += 1

            # This adds a method name into the set of method_names
            telemetry_stream.method_names.add(name)

            return result

        return wrapper

    return decorator


telemetry_stream: TelemetryStream = TelemetryStream()
