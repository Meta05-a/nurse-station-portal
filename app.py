from flask import Flask, render_template, jsonify, request, Response
import sqlite3
from datetime import datetime, timedelta
import csv
import io

app = Flask(__name__)
DB_FILE = "hospital.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            floor INTEGER NOT NULL,
            room TEXT NOT NULL,
            condition TEXT NOT NULL,
            doctor TEXT NOT NULL,
            admitted_date TEXT NOT NULL,
            discharge_date TEXT NOT NULL,
            notes TEXT
        )
    """)
    
    # Insert initial seed data if table is empty
    cursor.execute("SELECT COUNT(*) FROM patients")
    if cursor.fetchone()[0] == 0:
        today = datetime.now()
        seed_data = [
            ('P-101', 'Sarah Jenkins', 42, 1, '101-A', 'Post-Op Recovery', 'Dr. Arben Hoxha', 
             (today - timedelta(days=2)).strftime("%Y-%m-%d"), (today + timedelta(days=2)).strftime("%Y-%m-%d"), 
             'Vitals stable. Pain managed. Scheduled for physical therapy.'),
            ('P-102', 'Michael Chang', 67, 1, '104-B', 'Cardiac Observation', 'Dr. Elena Prifti', 
             (today - timedelta(days=4)).strftime("%Y-%m-%d"), (today + timedelta(days=1)).strftime("%Y-%m-%d"), 
             'EKG normal. Awaiting morning lab clearance.'),
            ('P-201', 'Elena Rostova', 29, 2, '202-A', 'Maternity', 'Dr. Drita Gjoni', 
             (today - timedelta(days=1)).strftime("%Y-%m-%d"), (today + timedelta(days=3)).strftime("%Y-%m-%d"), 
             'Infant feeding well. Routine post-natal observation.'),
            ('P-202', 'David Miller', 55, 2, '210-C', 'Pneumonia', 'Dr. Arben Hoxha', 
             (today - timedelta(days=5)).strftime("%Y-%m-%d"), (today + timedelta(days=4)).strftime("%Y-%m-%d"), 
             'Oxygen saturation 97% on room air. Continue IV antibiotics.'),
            ('P-301', 'Arthur Pendelton', 81, 3, '305-B', 'Orthopedic Surgery', 'Dr. Ilir Kola', 
             (today - timedelta(days=3)).strftime("%Y-%m-%d"), (today + timedelta(days=2)).strftime("%Y-%m-%d"), 
             'Assisted ambulatory mobility. Dressing changed at 08:00.')
        ]
        cursor.executemany("""
            INSERT INTO patients (patient_code, name, age, floor, room, condition, doctor, admitted_date, discharge_date, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, seed_data)
        conn.commit()
    conn.close()

init_db()

def calculate_days_remaining(discharge_date_str):
    discharge = datetime.strptime(discharge_date_str, "%Y-%m-%d").date()
    today = datetime.now().date()
    delta = (discharge - today).days
    return delta if delta >= 0 else 0

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/patients", methods=["GET"])
def get_patients():
    floor_filter = request.args.get("floor")
    conn = get_db_connection()
    
    if floor_filter and floor_filter != "all":
        try:
            target_floor = int(floor_filter)
            rows = conn.execute("SELECT * FROM patients WHERE floor = ? ORDER BY id DESC", (target_floor,)).fetchall()
        except ValueError:
            return jsonify({"error": "Invalid floor parameter"}), 400
    else:
        rows = conn.execute("SELECT * FROM patients ORDER BY id DESC").fetchall()
        
    conn.close()
    
    patients = []
    for row in rows:
        p = dict(row)
        p["days_remaining"] = calculate_days_remaining(p["discharge_date"])
        patients.append(p)
        
    return jsonify(patients)

@app.route("/api/patients/<int:patient_id>", methods=["GET"])
def get_patient(patient_id):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "Patient record not found"}), 404
    
    patient = dict(row)
    patient["days_remaining"] = calculate_days_remaining(patient["discharge_date"])
    return jsonify(patient)

@app.route("/api/patients", methods=["POST"])
def add_patient():
    data = request.json
    required_fields = ["name", "age", "floor", "room", "condition", "doctor", "stay_days"]
    for field in required_fields:
        if field not in data or data[field] == "":
            return jsonify({"error": f"Missing required field: {field}"}), 400

    today = datetime.now()
    admitted_date = today.strftime("%Y-%m-%d")
    stay_days = int(data["stay_days"])
    discharge_date = (today + timedelta(days=stay_days)).strftime("%Y-%m-%d")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Generate unique code
    cursor.execute("SELECT MAX(id) FROM patients")
    max_id = cursor.fetchone()[0] or 100
    patient_code = f"P-{max_id + 1}"
    
    cursor.execute("""
        INSERT INTO patients (patient_code, name, age, floor, room, condition, doctor, admitted_date, discharge_date, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (patient_code, data["name"], int(data["age"]), int(data["floor"]), data["room"],
          data["condition"], data["doctor"], admitted_date, discharge_date, data.get("notes", "")))
    
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    
    return jsonify({"message": "Patient created successfully", "id": new_id}), 201

@app.route("/api/patients/<int:patient_id>", methods=["PUT"])
def update_patient(patient_id):
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    
    row = cursor.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Patient record not found"}), 404

    today = datetime.now()
    stay_days = int(data.get("stay_days", 0))
    discharge_date = (today + timedelta(days=stay_days)).strftime("%Y-%m-%d")

    cursor.execute("""
        UPDATE patients 
        SET name = ?, age = ?, floor = ?, room = ?, condition = ?, doctor = ?, discharge_date = ?, notes = ?
        WHERE id = ?
    """, (data["name"], int(data["age"]), int(data["floor"]), data["room"],
          data["condition"], data["doctor"], discharge_date, data.get("notes", ""), patient_id))
    
    conn.commit()
    conn.close()
    return jsonify({"message": "Patient record updated successfully"})

@app.route("/api/patients/<int:patient_id>", methods=["DELETE"])
def discharge_patient(patient_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Patient officially discharged and archived."})

@app.route("/api/patients/<int:patient_id>/export", methods=["GET"])
def export_patient_csv(patient_id):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Patient record not found"}), 404

    patient = dict(row)
    days_left = calculate_days_remaining(patient["discharge_date"])

    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(["Field", "Value"])
    writer.writerow(["Patient ID Code", patient["patient_code"]])
    writer.writerow(["Full Name", patient["name"]])
    writer.writerow(["Age", patient["age"]])
    writer.writerow(["Floor Level", f"Floor {patient['floor']}"])
    writer.writerow(["Room Number", patient["room"]])
    writer.writerow(["Medical Condition", patient["condition"]])
    writer.writerow(["Assigned Doctor", patient["doctor"]])
    writer.writerow(["Admission Date", patient["admitted_date"]])
    writer.writerow(["Scheduled Discharge Date", patient["discharge_date"]])
    writer.writerow(["Estimated Time Remaining", f"{days_left} Days"])
    writer.writerow(["Clinical Notes", patient["notes"]])
    
    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=Patient_Record_{patient['patient_code']}.csv"
    return response

if __name__ == "__main__":
    app.run(debug=True, port=5000)
