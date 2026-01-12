"""Configuration models for ESPro."""

from pydantic import BaseModel, Field


class ScannerConfig(BaseModel):
    """Scanner configuration."""

    default_network: str = "192.168.1.0/24"
    port: int = Field(default=6053, ge=1, le=65535)
    timeout: float = Field(default=5.0, gt=0)
    parallel_scans: int = Field(default=50, ge=1, le=255)


class ESProConfig(BaseModel):
    """Main ESPro configuration."""

    scanning: ScannerConfig = Field(default_factory=ScannerConfig)


ScanningConfig = ScannerConfig
