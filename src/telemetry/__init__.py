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

    def return_data_point(self) -> dict:
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
        self.method_names: set[str] = set()
        self.telemetry_data: dict[int, Telemetry] = {}

    async def capture_error(self, method_name: str, error_type: str):
        """
        Handler to capture error telemetry
        """
        current_minute: int = int(time.time() / 60)
        error_metric = ErrorMetrics(method_name=method_name, error_type=error_type)
        if self.telemetry_data.get(current_minute, False):
            await self.telemetry_data[current_minute].add_error_metric(error_metric=error_metric)
        else:
            telemetry = Telemetry()
            await telemetry.add_error_metric(error_metric=error_metric)
            self.telemetry_data.update({f'{current_minute}': telemetry})

    async def capture_time_metrics(self, name, current_minute, start_time):
        time_metrics: TimeMetrics = TimeMetrics(method_name=name, latency=(time.monotonic() - start_time))
        if self.telemetry_data.get(current_minute, False):
            await self.telemetry_data[current_minute].add_timing_data(timing_data=time_metrics)
        else:
            telemetry: Telemetry = Telemetry()
            await telemetry.add_timing_data(timing_data=time_metrics)
            self.telemetry_data.update(current_minute=telemetry)
            self.elapsed_time_minutes += 1

    async def return_data_stream(self) -> tuple[time, dict[str, int | list[dict[str, str | int]]]]:
        for _time, data in self.telemetry_data.items():
            yield _time, data.return_data_point()

    @property
    def highest_errors_per_minute(self) -> int:
        return max(*[telemetry.error_count for telemetry in self.telemetry_data.values()])

    @property
    def lowest_errors_per_minute(self) -> int:
        return min(*[telemetry.error_count for telemetry in self.telemetry_data.values()])

    @property
    def highest_latency_per_method(self) -> dict[str, float]:
        """
        **highest_latency_per_method**
            returns method names with their highest latency numbers
        :return:
        """
        def get_latency(metric: Telemetry) -> float:
            _metric_data: dict[str, dict[str, str | float]] = metric.return_data_point()
            return _metric_data.get('timing_data', {}).get('latency')

        method_max_latency = dict()
        for method in list(self.method_names):
            method_max_latency.update({f'{method}': max(*[lambda metric: get_latency(metric)
                                                          for metric in self.telemetry_data.values()])})
        return method_max_latency

    @property
    def lowest_latency_per_method(self) -> dict[str, float]:
        """
        **lowest_latency_per_method
            returns method names with their lowest latency numbers
        :return:
        """
        def get_latency(metric: Telemetry) -> float:
            _metric_data: dict[str, dict[str, str | float]] = metric.return_data_point()
            return _metric_data.get('timing_data', {}).get('latency')

        method_max_latency = dict()
        for method in list(self.method_names):
            method_max_latency.update({
                f'{method}': min(*[lambda metric: get_latency(metric=metric) for metric in self.telemetry_data.values()])})
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


def capture_telemetry(name: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_minute: int = int(time.time() / 60)
            start_time: float = time.monotonic()
            # TODO add try Except Clauses for all error types then capture the data on the telemetry stream
            try:
                result = await func(*args, **kwargs)
            except Exception as e:
                telemetry_logger.error(e)
                await telemetry_stream.capture_error(method_name=name, error_type=e)
                result = None
            finally:
                await telemetry_stream.capture_time_metrics(name=name, current_minute=current_minute, start_time=start_time)
                # This adds a method name into the set of method_names
                telemetry_stream.method_names.add(name)

            return result
        return wrapper

    return decorator


telemetry_stream: TelemetryStream = TelemetryStream()
