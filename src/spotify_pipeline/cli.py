"""C14 — CLI entrypoints (SPEC command names)."""

import typer

app = typer.Typer(
    name="spotify-pipeline",
    help="Spotify Charts → Web API → ReccoBeats batch pipeline.",
    no_args_is_help=True,
)


def _not_implemented(name: str) -> None:
    raise NotImplementedError(f"SPEC C14 CLI `{name}` — not implemented yet")


@app.command("run")
def run_cmd(
    chart_date: str = typer.Option(
        ..., "--chart-date", help="Watermark chart date (YYYY-MM-DD)"
    ),
    chart_type: str = typer.Option(
        "weekly_top_songs",
        "--chart-type",
        help="Chart type, e.g. weekly_top_songs",
    ),
    country: str = typer.Option("global", "--country", help="Chart country / region"),
    no_fs: bool = typer.Option(
        False, "--no-fs", help="Skip dual-write under data/bronze/"
    ),
    skip_ingest: bool = typer.Option(
        False,
        "--skip-ingest",
        help="Skip ingest-charts; require existing Bronze raw_charts",
    ),
    offline: bool = typer.Option(
        False, "--offline", help="Use fixtures only (no live network)"
    ),
    report: bool = typer.Option(False, "--report", help="Print Gold summary after run"),
) -> None:
    """Bronze Stage 4 cycle: ingest → extract once → Spotify ∥ ReccoBeats.

    Silver/Gold/report still deferred. Offline fixtures not implemented yet.
    """
    if offline:
        typer.secho(
            "FAIL: --offline not implemented yet (fixtures / full medallion later)",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)
    if report:
        typer.secho(
            "WARN: --report ignored until Gold is implemented",
            fg=typer.colors.YELLOW,
            err=True,
        )

    from spotify_pipeline.pipeline.run import RunError, run_bronze
    from spotify_pipeline.state.watermark import Watermark, WatermarkError

    try:
        watermark = Watermark.parse(chart_date, chart_type, country)
        result = run_bronze(
            watermark,
            write_fs=not no_fs,
            ingest=not skip_ingest,
        )
    except (WatermarkError, RunError) as exc:
        typer.secho(f"FAIL: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    ex = result.get("extract") or {}
    sp = result.get("enrich_spotify") or {}
    rb = result.get("enrich_reccobeats") or {}
    typer.echo(
        "OK run (bronze) "
        f"watermark={result['watermark']} "
        f"extract_tracks={ex.get('track_count')} "
        f"spotify_inserted={sp.get('inserted')} "
        f"reccobeats_inserted={rb.get('inserted')} "
        f"run_id={result['run_id']}"
    )


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
def enrich_spotify_cmd(
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
    """SPEC C9 — enrich Spotify metadata → Bronze for one watermark."""
    from spotify_pipeline.pipeline.enrich_spotify import (
        EnrichSpotifyError,
        enrich_spotify,
    )
    from spotify_pipeline.state.watermark import Watermark, WatermarkError

    try:
        watermark = Watermark.parse(chart_date, chart_type, country)
        result = enrich_spotify(watermark, write_fs=not no_fs)
    except (WatermarkError, EnrichSpotifyError) as exc:
        typer.secho(f"FAIL: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(
        "OK enrich-spotify "
        f"watermark={result['watermark']} "
        f"tracks={result['track_count']} "
        f"artists={result['artist_count']} "
        f"inserted={result['inserted']} "
        f"run_id={result['run_id']}"
    )


@app.command("enrich-reccobeats")
def enrich_reccobeats_cmd(
    chart_date: str = typer.Option(
        ..., "--chart-date", help="Watermark chart date (YYYY-MM-DD)"
    ),
    chart_type: str = typer.Option(
        "weekly_top_songs",
        "--chart-type",
        help="Must be weekly_top_songs for audio-features",
    ),
    country: str = typer.Option("global", "--country", help="Chart country / region"),
    no_fs: bool = typer.Option(
        False, "--no-fs", help="Skip dual-write under data/bronze/"
    ),
) -> None:
    """SPEC C9 — enrich ReccoBeats features → Bronze for one watermark."""
    from spotify_pipeline.pipeline.enrich_reccobeats import (
        EnrichReccoBeatsError,
        enrich_reccobeats,
    )
    from spotify_pipeline.state.watermark import Watermark, WatermarkError

    try:
        watermark = Watermark.parse(chart_date, chart_type, country)
        result = enrich_reccobeats(watermark, write_fs=not no_fs)
    except (WatermarkError, EnrichReccoBeatsError) as exc:
        typer.secho(f"FAIL: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(
        "OK enrich-reccobeats "
        f"watermark={result['watermark']} "
        f"tracks={result['track_count']} "
        f"batches={result['batch_count']} "
        f"hits={result['hits']} "
        f"misses={result['misses']} "
        f"inserted={result['inserted']} "
        f"run_id={result['run_id']}"
    )


@app.command("build-silver")
def build_silver(
    chart_date: str = typer.Option(
        ..., "--chart-date", help="Watermark chart date (YYYY-MM-DD)"
    ),
    chart_type: str = typer.Option(
        "weekly_top_songs",
        "--chart-type",
        help="MVP: weekly_top_songs (fact + dims + features)",
    ),
    country: str = typer.Option("global", "--country", help="Chart country / region"),
) -> None:
    """SPEC C10 — Silver one-pass (W1–W4): fact → dims → bridge → features.

    Does not wire into `run` (SQ-11 deferred). Gold/offline still separate.
    """
    from spotify_pipeline.pipeline.silver import SilverError, build_silver
    from spotify_pipeline.state.watermark import Watermark, WatermarkError

    try:
        watermark = Watermark.parse(chart_date, chart_type, country)
        result = build_silver(watermark)
    except (WatermarkError, SilverError) as exc:
        typer.secho(f"FAIL: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    fact = result.fact
    dim = result.dim_track
    artists = result.artist_bridge
    features = result.features
    typer.echo(
        "OK build-silver "
        f"watermark={result.watermark} "
        f"fact_upserted={fact.upserted} "
        f"dim_track_upserted={dim.upserted} "
        f"dim_track_missed={dim.missed} "
        f"artists_upserted={artists.artists_upserted} "
        f"bridges_upserted={artists.bridges_upserted} "
        f"features_hits={features.hits} "
        f"features_misses={features.misses} "
        f"raw_charts_id={fact.raw_charts_id} "
        f"run_id={result.run_id}"
    )


@app.command("build-gold")
def build_gold_cmd(
    chart_date: str = typer.Option(
        ..., "--chart-date", help="Watermark chart date (YYYY-MM-DD)"
    ),
    chart_type: str = typer.Option(
        "weekly_top_songs",
        "--chart-type",
        help="MVP: weekly_top_songs",
    ),
    country: str = typer.Option("global", "--country", help="Chart country / region"),
) -> None:
    """SPEC C11 — Gold one-pass (coverage / movers / mood / popularity skip).

    Does not wire into `run` (GQ-8). SCD2 formal table deferred (GQ-5).
    """
    from spotify_pipeline.pipeline.gold import GoldError, build_gold
    from spotify_pipeline.state.watermark import Watermark, WatermarkError

    try:
        watermark = Watermark.parse(chart_date, chart_type, country)
        result = build_gold(watermark)
    except (WatermarkError, GoldError) as exc:
        typer.secho(f"FAIL: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    cov = result.coverage
    if cov is None:
        cov_part = "coverage=none"
    else:
        pct = cov.features_found_pct
        pct_s = "null" if pct is None else str(pct)
        cov_part = (
            f"chart_rows={cov.chart_rows} "
            f"features_found_rows={cov.features_found_rows} "
            f"features_found_pct={pct_s}"
        )
    pop = (
        f"popularity_skipped=true reason={result.popularity_reason}"
        if result.popularity_skipped
        else f"popularity_pairs={result.popularity_pairs}"
    )
    typer.echo(
        "OK build-gold "
        f"watermark={result.watermark} "
        f"{cov_part} "
        f"missing_top={result.missing_count} "
        f"movers={result.movers_count} "
        f"mood={result.mood_count} "
        f"{pop} "
        f"scd2={result.scd2_status}"
    )


@app.command("backfill-features")
def backfill_features() -> None:
    """SPEC C12 — re-query ReccoBeats where features_found=false."""
    _not_implemented("backfill-features")


if __name__ == "__main__":
    app()
