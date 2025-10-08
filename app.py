"""Baby Shower Guessing Game (minimal CSV version).

This Flask app serves a simple form for guests to submit baby name, gender,
and weight guesses. Submissions are appended to a CSV file in ./data.
A hidden test endpoint '/_results' renders a basic HTML table of rows.
"""

from __future__ import annotations

import csv
import os
from datetime import datetime
from typing import List, Dict, Tuple

from flask import Flask, redirect, render_template, request, url_for

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

DATA_DIR = "data"
CSV_PATH = os.path.join(DATA_DIR, "guesses.csv")
CSV_HEADERS = [
    "timestamp", "guest_name", "baby_name", "gender",
    "due_date", "due_time", "weight_kg"
]
SHOW_RESULTS = os.getenv("SHOW_RESULTS", "false").lower() == "true"
RESULTS_PASSWORD = os.getenv("RESULTS_PASSWORD", "")



# -----------------------------------------------------------------------------
# Storage helpers
# -----------------------------------------------------------------------------

def ensure_csv_exists() -> None:
    """Create the data directory and CSV file with headers if missing."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as header_file:
            header_writer = csv.writer(header_file)
            header_writer.writerow(CSV_HEADERS)


def append_guess(
    guest_name: str,
    baby_name: str,
    gender: str,
    due_date: str,
    due_time: str,
    weight_kg: str,
) -> None:
    """Append a single guess row to the CSV file."""
    timestamp = datetime.utcnow().isoformat()
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as append_file:
        append_writer = csv.writer(append_file)
        append_writer.writerow(
            [timestamp, guest_name, baby_name, gender, due_date, due_time, weight_kg]
            )


def read_guesses() -> Tuple[List[Dict[str, str]], List[str]]:
    """Read all guesses from CSV and return (rows, headers)."""
    if not os.path.exists(CSV_PATH):
        return [], CSV_HEADERS
    with open(CSV_PATH, newline="", encoding="utf-8") as csv_file:
        dict_reader = csv.DictReader(csv_file)
        rows: List[Dict[str, str]] = list(dict_reader)
        headers = dict_reader.fieldnames or CSV_HEADERS
    return rows, headers


# -----------------------------------------------------------------------------
# App factory (keeps globals tidy for linters & testing)
# -----------------------------------------------------------------------------

def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Make sure data directory and CSV exist
    ensure_csv_exists()

    @app.route("/", methods=["GET"])
    def index():
        """Render the main form page."""
        return render_template("index.html")

    @app.route("/submit", methods=["POST"])
    def submit():
        """Handle form submission and persist to CSV, then show a thank-you page."""
        guest_name = (request.form.get("guest_name") or "").strip()
        baby_name  = (request.form.get("baby_name") or "").strip()
        gender     = (request.form.get("gender") or "").strip()
        due_date   = (request.form.get("due_date") or "").strip()   # YYYY-MM-DD
        due_time   = (request.form.get("due_time") or "").strip()   # HH:MM
        weight_kg  = (request.form.get("weight") or "").strip()

        # Minimal required field validation
        if not guest_name:
            # No flash here to keep deps minimal; just bounce back.
            return redirect(url_for("index"))

        append_guess(guest_name, baby_name, gender, due_date, due_time, weight_kg)
        return redirect(url_for("thanks"))

    @app.route("/thanks", methods=["GET"])
    def thanks():
        """Render a simple thank-you page."""
        return render_template("thanks.html")

    @app.route("/results", methods=["GET", "POST"])
    def results():
        """Results page using a template for table rendering."""
        if not SHOW_RESULTS:
            # Optional password protection
            if request.method == "POST":
                password = (request.form.get("password") or "").strip()
                if password == RESULTS_PASSWORD:
                    rows, headers = read_guesses()
                    return render_template("results.html", rows=rows, headers=headers)
                return render_template(
                    "results_locked.html",
                    error="Incorrect password. Please try again.",
                )
            # If GET and results hidden
            return render_template("results_locked.html")

        # If SHOW_RESULTS=true
        rows, headers = read_guesses()
        return render_template("results.html", rows=rows, headers=headers)

    return app


# -----------------------------------------------------------------------------
# Entrypoint
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    # Running via `python app.py`
    create_app().run(debug=True)
