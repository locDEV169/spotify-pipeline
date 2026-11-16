"""C14 — CLI entrypoints (SPEC command names). Stubs until pipeline is implemented."""

from typing import Optional

import typer

app = typer.Typer(
    name="spotify-pipeline",
    help="Spotify Charts → Web API → ReccoBeats batch pipeline (scaffold stubs).",
    no_args_is_help=True,
)


def _not_implemented(name: str) -> None:
    raise NotImplementedError(f"SPEC C14 CLI `{name}` — not implemented yet")


@app.command("run")
def run(
    chart_date: str = typer.Option(..., "--chart-date", help="Watermark chart date (YYYY-MM-DD)"),
    chart_type: str = typer.Option(
        "weekly_top_songs",
        "--chart-type",
        help="Chart type, e.g. weekly_top_songs",
    ),
    country: str = typer.Option("global", "--country", help="Chart country / region"),
    offline: bool = typer.Option(False, "--offline", help="Use fixtures only (no live network)"),
    report: bool = typer.Option(False, "--report", help="Print Gold summary after run"),
) -> None:
    """Full pipeline for one watermark (SPEC C14 / C9–C13)."""
    _ = (chart_date, chart_type, country, offline, report)
    _not_implemented("run")


@app.command("ingest-charts")
def ingest_charts(
    chart_date: str = typer.Option(..., "--chart-date"),
    chart_type: str = typer.Option("weekly_top_songs", "--chart-type"),
    country: str = typer.Option("global", "--country"),
) -> None:
    """SPEC C9 — ingest Charts → Bronze."""
    _ = (chart_date, chart_type, country)
    _not_implemented("ingest-charts")


@app.command("enrich-spotify")
def enrich_spotify(
    chart_date: Optional[str] = typer.Option(None, "--chart-date"),
) -> None:
    """SPEC C9 — enrich Spotify metadata → Bronze."""
    _ = chart_date
    _not_implemented("enrich-spotify")


@app.command("enrich-reccobeats")
def enrich_reccobeats(
    chart_date: Optional[str] = typer.Option(None, "--chart-date"),
) -> None:
    """SPEC C9 — enrich ReccoBeats features → Bronze."""
    _ = chart_date
    _not_implemented("enrich-reccobeats")


@app.command("build-silver")
def build_silver() -> None:
    """SPEC C10 — Silver tables + LEFT JOIN."""
    _not_implemented("build-silver")


@app.command("build-gold")
def build_gold() -> None:
    """SPEC C11 — Gold summary / movers / mood."""
    _not_implemented("build-gold")


@app.command("backfill-features")
def backfill_features() -> None:
    """SPEC C12 — re-query ReccoBeats where features_found=false."""
    _not_implemented("backfill-features")


if __name__ == "__main__":
    app()
