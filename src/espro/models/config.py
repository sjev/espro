"""Configuration models."""

from pydantic import BaseModel, Field


class ScanningConfig(BaseModel):
    """Scanning configuration."""

    default_network: str = "192.168.1.0/24"
    port: int = Field(default=6053, ge=1, le=65535)
    timeout: float = Field(default=5.0, gt=0)
    parallel_scans: int = Field(default=50, ge=1, le=255)


class EsProConfig(BaseModel):
    """Main ESPro configuration."""

    scanning: ScanningConfig = Field(default_factory=ScanningConfig)
