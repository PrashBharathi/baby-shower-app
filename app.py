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
from flask_sqlalchemy import SQLAlchemy

from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, TimeField, DecimalField
from wtforms.validators import DataRequired, Length, Optional, NumberRange

from dotenv import load_dotenv
load_dotenv()

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

DB_PATH = "sqlite:///app.db"
db = SQLAlchemy()  # create globally, but init later inside the app factory



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

    # --- Configuration (these lines go here) ---
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-only-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = DB_PATH
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # --- Initialize extensions ---
    db.init_app(app)

    # --- Define your model here ---
    class Guess(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        timestamp = db.Column(db.String(32), nullable=False)
        guest_name = db.Column(db.String(80), nullable=False)
        baby_name = db.Column(db.String(120))
        gender = db.Column(db.String(16))
        due_date = db.Column(db.String(10))
        due_time = db.Column(db.String(5))
        weight_kg = db.Column(db.String(10))

    class GuessForm(FlaskForm):
        guest_name = StringField("Your Name", validators=[DataRequired(), Length(max=80)])
        baby_name  = StringField("Baby Name", validators=[Optional(), Length(max=120)])
        gender     = SelectField("Gender", choices=[("", "Not sure"), ("Boy", "Boy"), ("Girl", "Girl")])
        due_date   = DateField("Due Date", validators=[Optional()])
        due_time   = TimeField("Due Time", validators=[Optional()])
        weight     = DecimalField("Birth Weight (kg)", places=2,
                                validators=[Optional(), NumberRange(min=0, max=10)])


    # --- Create the database file if it doesn’t exist ---
    with app.app_context():
        db.create_all()

    @app.route("/", methods=["GET", "POST"])
    def index():
        form = GuessForm()
        if form.validate_on_submit():
            new_guess = Guess(
                timestamp=datetime.utcnow().isoformat(),
                guest_name=form.guest_name.data.strip(),
                baby_name=(form.baby_name.data or "").strip(),
                gender=form.gender.data or "",
                due_date=form.due_date.data.isoformat() if form.due_date.data else "",
                due_time=form.due_time.data.strftime("%H:%M") if form.due_time.data else "",
                weight_kg=str(form.weight.data) if form.weight.data is not None else "",
            )
            db.session.add(new_guess)
            db.session.commit()
            return redirect(url_for("thanks"))
        return render_template("index.html", form=form)


    @app.route("/thanks", methods=["GET"])
    def thanks():
        """Render a simple thank-you page."""
        return render_template("thanks.html")

    @app.route("/results", methods=["GET", "POST"])
    def results():
        """Results page using a template for table rendering."""
        guesses = Guess.query.order_by(Guess.id.asc()).all()
        headers = ["timestamp","guest_name","baby_name","gender","due_date","due_time","weight_kg"]
        rows = [{h: getattr(g, h) for h in headers} for g in guesses]
        return render_template("results.html", rows=rows, headers=headers)

    return app


# -----------------------------------------------------------------------------
# Entrypoint
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    # Running via `python app.py`
    create_app().run(debug=True)
