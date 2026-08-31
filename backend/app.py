from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

DATABASE = "landslide.db"
UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# ---------------- DATABASE ----------------

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT,
            latitude REAL,
            longitude REAL,
            rainfall REAL,
            soil_moisture REAL,
            slope REAL,
            risk_level TEXT,
            risk_score INTEGER,
            description TEXT,
            image TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


# ---------------- HOME ----------------

@app.route("/")
def home():
    return jsonify({
        "status": "success",
        "message": "AI Landslide Risk Monitoring Backend is Running",
        "version": "1.0"
    })


# ---------------- RISK PREDICTION ----------------

@app.route("/api/risk", methods=["POST"])
def calculate_risk():

    try:
        data = request.get_json() or {}

        rainfall = float(data.get("rainfall", 0))
        soil_moisture = float(data.get("soil_moisture", 0))
        slope = float(data.get("slope", 0))

        risk_score = 0

        # Rainfall
        if rainfall >= 150:
            risk_score += 40
        elif rainfall >= 80:
            risk_score += 25
        else:
            risk_score += 10

        # Soil Moisture
        if soil_moisture >= 80:
            risk_score += 30
        elif soil_moisture >= 50:
            risk_score += 20
        else:
            risk_score += 10

        # Slope
        if slope >= 35:
            risk_score += 30
        elif slope >= 20:
            risk_score += 20
        else:
            risk_score += 10

        # Risk Level
        if risk_score >= 75:
            risk_level = "HIGH"
            alert = True
            message = "High landslide risk. Immediate precautionary action recommended."

        elif risk_score >= 45:
            risk_level = "MEDIUM"
            alert = False
            message = "Moderate landslide risk. Continue monitoring conditions."

        else:
            risk_level = "LOW"
            alert = False
            message = "Low landslide risk under current conditions."

        return jsonify({
            "status": "success",
            "risk_score": risk_score,
            "risk_level": risk_level,
            "alert": alert,
            "message": message,
            "data": {
                "rainfall": rainfall,
                "soil_moisture": soil_moisture,
                "slope": slope
            }
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400


# ---------------- REPORT INCIDENT ----------------

@app.route("/api/report", methods=["POST"])
def report_incident():

    try:

        location = request.form.get("location", "")
        latitude = float(request.form.get("latitude", 0))
        longitude = float(request.form.get("longitude", 0))

        rainfall = float(request.form.get("rainfall", 0))
        soil_moisture = float(request.form.get("soil_moisture", 0))
        slope = float(request.form.get("slope", 0))

        description = request.form.get("description", "")

        # Calculate risk
        risk_score = 0

        if rainfall >= 150:
            risk_score += 40
        elif rainfall >= 80:
            risk_score += 25
        else:
            risk_score += 10

        if soil_moisture >= 80:
            risk_score += 30
        elif soil_moisture >= 50:
            risk_score += 20
        else:
            risk_score += 10

        if slope >= 35:
            risk_score += 30
        elif slope >= 20:
            risk_score += 20
        else:
            risk_score += 10

        if risk_score >= 75:
            risk_level = "HIGH"
        elif risk_score >= 45:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # Image upload
        image = request.files.get("image")
        image_name = ""

        if image and image.filename:

            image_name = datetime.now().strftime(
                "%Y%m%d%H%M%S"
            ) + "_" + image.filename

            image.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    image_name
                )
            )

        # Save report
        conn = get_db()

        conn.execute("""
            INSERT INTO reports
            (
                location,
                latitude,
                longitude,
                rainfall,
                soil_moisture,
                slope,
                risk_level,
                risk_score,
                description,
                image,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            location,
            latitude,
            longitude,
            rainfall,
            soil_moisture,
            slope,
            risk_level,
            risk_score,
            description,
            image_name,
            datetime.now().isoformat()
        ))

        conn.commit()
        report_id = conn.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0]

        conn.close()

        return jsonify({
            "status": "success",
            "message": "Incident report submitted successfully",
            "report_id": report_id,
            "risk_level": risk_level,
            "risk_score": risk_score
        })

    except Exception as e:

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400


# ---------------- GET ALL REPORTS ----------------

@app.route("/api/reports", methods=["GET"])
def get_reports():

    conn = get_db()

    reports = conn.execute("""
        SELECT *
        FROM reports
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    result = []

    for report in reports:
        result.append(dict(report))

    return jsonify({
        "status": "success",
        "total": len(result),
        "reports": result
    })


# ---------------- DASHBOARD ----------------

@app.route("/api/dashboard", methods=["GET"])
def dashboard():

    conn = get_db()

    total = conn.execute(
        "SELECT COUNT(*) FROM reports"
    ).fetchone()[0]

    high = conn.execute(
        "SELECT COUNT(*) FROM reports WHERE risk_level='HIGH'"
    ).fetchone()[0]

    medium = conn.execute(
        "SELECT COUNT(*) FROM reports WHERE risk_level='MEDIUM'"
    ).fetchone()[0]

    low = conn.execute(
        "SELECT COUNT(*) FROM reports WHERE risk_level='LOW'"
    ).fetchone()[0]

    conn.close()

    return jsonify({
        "status": "success",
        "dashboard": {
            "total_reports": total,
            "high_risk": high,
            "medium_risk": medium,
            "low_risk": low
        }
    })


# ---------------- HIGH RISK ALERTS ----------------

@app.route("/api/alerts", methods=["GET"])
def alerts():

    conn = get_db()

    high_risk_reports = conn.execute("""
        SELECT *
        FROM reports
        WHERE risk_level='HIGH'
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    alerts_list = []

    for report in high_risk_reports:

        alerts_list.append({
            "id": report["id"],
            "location": report["location"],
            "risk_level": report["risk_level"],
            "risk_score": report["risk_score"],
            "message": "⚠️ HIGH LANDSLIDE RISK ALERT",
            "created_at": report["created_at"]
        })

    return jsonify({
        "status": "success",
        "alert_count": len(alerts_list),
        "alerts": alerts_list
    })


# ---------------- HEALTH CHECK ----------------

@app.route("/api/health", methods=["GET"])
def health():

    return jsonify({
        "status": "online",
        "service": "Landslide Risk Monitoring API"
    })


# ---------------- START SERVER ----------------

if __name__ == "__main__":

    init_database()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
