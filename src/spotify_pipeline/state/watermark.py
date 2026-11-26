"""SPEC C7 — Watermark (chart_date, chart_type, country).

One pipeline run = one watermark. Fail fast on invalid values.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# MVP + known chart views from Charts public/v0 helpers
KNOWN_CHART_TYPES = frozenset(
    {
        "weekly_top_songs",
        "weekly_top_artists",
        "weekly_top_albums",
    }
)


class WatermarkError(ValueError):
    """Raised when watermark fields are missing or invalid."""


_THURSDAY = 3  # date.weekday()


def chart_date_before(run_end: date) -> str:
    """SPEC v2 Q8a: most recent Thursday strictly before ``run_end`` (YYYY-MM-DD).

    ``run_end`` = the scheduled run's ``data_interval_end`` as a local date
    (Mon 09:00 → the Thursday 4 days earlier).
    """
    days_back = (run_end.weekday() - _THURSDAY) % 7 or 7
    return (run_end - timedelta(days=days_back)).isoformat()


@dataclass(frozen=True, slots=True)
class Watermark:
    """Pipeline grain: chart_date × chart_type × country."""

    chart_date: str
    chart_type: str
    country: str

    @classmethod
    def parse(
        cls,
        chart_date: str,
        chart_type: str = "weekly_top_songs",
        country: str = "global",
    ) -> Watermark:
        """Build a watermark; fail fast on empty / bad date / bad type."""
        date = (chart_date or "").strip()
        ctype = (chart_type or "").strip().lower()
        ctry = (country or "").strip().lower()

        if not date:
            raise WatermarkError("chart_date is required (YYYY-MM-DD)")
        if not _DATE_RE.match(date):
            raise WatermarkError(f"chart_date must be YYYY-MM-DD, got {date!r}")
        if not ctype:
            raise WatermarkError("chart_type is required")
        if ctype not in KNOWN_CHART_TYPES:
            raise WatermarkError(
                f"unknown chart_type {ctype!r}; expected one of "
                f"{sorted(KNOWN_CHART_TYPES)}"
            )
        if not ctry:
            raise WatermarkError("country is required")

        return cls(chart_date=date, chart_type=ctype, country=ctry)

    def matches(
        self,
        chart_date: str | None,
        chart_type: str,
        country: str,
    ) -> bool:
        """True if live view watermark equals this watermark."""
        if not chart_date:
            return False
        return (
            chart_date == self.chart_date
            and (chart_type or "").strip().lower() == self.chart_type
            and (country or "").strip().lower() == self.country
        )

    def as_tuple(self) -> tuple[str, str, str]:
        return (self.chart_date, self.chart_type, self.country)
