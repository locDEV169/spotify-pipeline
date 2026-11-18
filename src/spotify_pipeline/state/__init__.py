"""Watermark (chart_date, chart_type, country) only. No API calls."""

from spotify_pipeline.state.watermark import Watermark, WatermarkError

__all__ = ["Watermark", "WatermarkError"]
