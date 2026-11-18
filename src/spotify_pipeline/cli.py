"""C14 — CLI entrypoints (SPEC command names)."""

from typing import Optional

import typer

app = typer.Typer(
    name="spotify-pipeline",
    help="Spotify Charts → Web API → ReccoBeats batch pipeline.",
    no_args_is_help=True,
)


def _not_implemented(name: str) -> None:
    raise NotImplementedError(f"SPEC C14 CLI `{name}` — not implemented yet")


@app.command("run")
def run(
    chart_date: str = typer.Option(
        ..., "--chart-date", help="Watermark chart date (YYYY-MM-DD)"
    ),
    chart_type: str = typer.Option(
        "weekly_top_songs",
        "--chart-type",
        help="Chart type, e.g. weekly_top_songs",
    ),
    country: str = typer.Option("global", "--country", help="Chart country / region"),
    offline: bool = typer.Option(
        False, "--offline", help="Use fixtures only (no live network)"
    ),
    report: bool = typer.Option(False, "--report", help="Print Gold summary after run"),
) -> None:
    """Full pipeline for one watermark (SPEC C14 / C9–C13)."""
    _ = (chart_date, chart_type, country, offline, report)
    _not_implemented("run")


@app.command("ingest-charts")
def ingest_charts_cmd(
    chart_date: str = typer.Option(
        ..., "--chart-date", help="Watermark chart date (YYYY-MM-DD)"
    ),
    chart_type: str = typer.Option(
        "weekly_top_songs",
        "--chart-type",
        help="e.g. weekly_top_songs | weekly_top_artists",
    ),
    country: str = typer.Option("global", "--country", help="Chart country / region"),
    no_fs: bool = typer.Option(
        False, "--no-fs", help="Skip dual-write under data/bronze/"
    ),
) -> None:
    """SPEC C9 — ingest Charts public/v0 → Bronze for one watermark."""
    from spotify_pipeline.pipeline.ingest_charts import (
        IngestChartsError,
        ingest_charts,
    )
    from spotify_pipeline.state.watermark import Watermark, WatermarkError

    try:
        watermark = Watermark.parse(chart_date, chart_type, country)
        result = ingest_charts(watermark, write_fs=not no_fs)
    except (WatermarkError, IngestChartsError) as exc:
        typer.secho(f"FAIL: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(
        "OK ingest-charts "
        f"watermark={result['watermark']} "
        f"entries={result['entry_count']} "
        f"run_id={result['run_id']}"
    )


@app.command("enrich-spotify")
def enrich_spotify(
    chart_date: Optional[str] = typer.Option(None, "--chart-date"),  # noqa: UP045
) -> None:
    """SPEC C9 — enrich Spotify metadata → Bronze."""
    _ = chart_date
    _not_implemented("enrich-spotify")


@app.command("enrich-reccobeats")
def enrich_reccobeats(
    chart_date: Optional[str] = typer.Option(None, "--chart-date"),  # noqa: UP045
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
