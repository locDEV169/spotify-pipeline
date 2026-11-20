"""HTTP routes, request validation and safe error responses."""

from datetime import date

from flask import Blueprint, current_app, jsonify, request

from . import charts

blueprint = Blueprint("api", __name__, url_prefix="/api")


@blueprint.get("/health")
def health():
    return jsonify(status="ok", service="spotify-pipeline")


@blueprint.get("/charts")
def chart_data():
    week = request.args.get("week")
    if week is not None:
        try:
            if date.fromisoformat(week).isoformat() != week:
                raise ValueError
        except ValueError:
            return jsonify(error="week must be a valid YYYY-MM-DD date"), 400
    try:
        return jsonify(charts.read_chart(week))
    except charts.ChartNotFound:
        return jsonify(error="No chart available for this week"), 404
    except Exception as exc:
        # Database exception messages can contain connection details.
        current_app.logger.error("Chart read failed (%s)", type(exc).__name__)
        return jsonify(
            error="Chart data is unavailable. Check the backend database connection."
        ), 503
