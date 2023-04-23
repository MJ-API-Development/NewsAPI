import time

from pydantic import BaseModel, Field


class TimeMetrics(BaseModel):
    """
        **TimeMetrics**
        this model is used to send time metrics
    """
    last_reboot: int = Field(default_factory=lambda: int(time.monotonic()))
    highest_cron_latency: int = Field(default=0)
    lowest_cron_latency: int = Field(default=0)
    highest_parse_latency: int = Field(default=0)
    lowest_parse_latency: int = Field(default=0)

    class Config:
        title = "Financial News Parser Time Metrics Data"


class Telemetry(BaseModel):
    """
    **Telemetry**
        this model is used to send telemetry data
        to the admin about this microservice
    """
    timing_data: TimeMetrics = TimeMetrics()
    total_errors_cron_api: int = Field(default=0)
    total_errors_parser_yahoo: int = Field(default=0)
    error_per_minute_cron_api: int = Field(default=0)
    error_per_minute_parser_api: int = Field(default=0)
    log_stream_data_delayed: str = Field()

    class Config:
        title = "Financial News Parser Telemetry Data"
