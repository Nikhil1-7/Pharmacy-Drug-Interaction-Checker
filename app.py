from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    session
)

import sqlite3
from datetime import datetime
from functools import wraps

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)


# ============================================================
# FLASK APPLICATION
# ============================================================

app = Flask(__name__)

app.secret_key = "pharmasafe_secret_key_2026"

DATABASE = "pharmacy.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db():

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# LOGIN REQUIRED
# ============================================================

def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "employee_id" not in session:

            return redirect(
                url_for("login")
            )

        return function(*args, **kwargs)

    return wrapper


# ============================================================
# MANAGER REQUIRED
# ============================================================

def manager_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "employee_id" not in session:

            return redirect(
                url_for("login")
            )

        if session.get("role") != "Manager":

            return (
                "Access denied. Manager permission required.",
                403
            )

        return function(*args, **kwargs)

    return wrapper


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def initialize_database():

    conn = get_db()

    cursor = conn.cursor()

    # ========================================================
    # CHECK MEDICINES TABLE
    # ========================================================

    cursor.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name='medicines'"
    )

    medicines_table = cursor.fetchone()

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Your existing database has:
    #
    # id
    # medicine_name
    # generic_name
    # quantity
    # price
    # created_at
    #
    # So we DO NOT replace this table with brand_name/salts.
    # --------------------------------------------------------

    if not medicines_table:

        cursor.execute("""
            CREATE TABLE medicines (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                medicine_name TEXT NOT NULL,

                generic_name TEXT,

                quantity INTEGER DEFAULT 0,

                price REAL DEFAULT 0,

                created_at TEXT NOT NULL

            )
        """)

    # ========================================================
    # INTERACTIONS TABLE
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interactions (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            salt1 TEXT NOT NULL,

            salt2 TEXT NOT NULL,

            severity TEXT NOT NULL,

            warning TEXT NOT NULL

        )
    """)

    # ========================================================
    # BILLS TABLE
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bills (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            patient_name TEXT NOT NULL,

            bill_date TEXT NOT NULL,

            total_amount REAL NOT NULL,

            status TEXT NOT NULL

        )
    """)

    # ========================================================
    # CHECK BILL COLUMNS
    # ========================================================

    cursor.execute(
        "PRAGMA table_info(bills)"
    )

    bill_columns = [
        row["name"]
        for row in cursor.fetchall()
    ]

    if "prescription_number" not in bill_columns:

        cursor.execute("""
            ALTER TABLE bills
            ADD COLUMN prescription_number TEXT
        """)

    if "employee_id" not in bill_columns:

        cursor.execute("""
            ALTER TABLE bills
            ADD COLUMN employee_id INTEGER
        """)

    # ========================================================
    # EMPLOYEES TABLE
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            employee_name TEXT,

            username TEXT,

            password TEXT,

            role TEXT DEFAULT 'Employee',

            active INTEGER DEFAULT 1

        )
    """)

    # ========================================================
    # EMPLOYEE TABLE MIGRATION
    # ========================================================

    cursor.execute(
        "PRAGMA table_info(employees)"
    )

    employee_columns = [
        row["name"]
        for row in cursor.fetchall()
    ]

    if "employee_name" not in employee_columns:

        cursor.execute("""
            ALTER TABLE employees
            ADD COLUMN employee_name TEXT
        """)

    if "username" not in employee_columns:

        cursor.execute("""
            ALTER TABLE employees
            ADD COLUMN username TEXT
        """)

    if "password" not in employee_columns:

        cursor.execute("""
            ALTER TABLE employees
            ADD COLUMN password TEXT
        """)

    if "role" not in employee_columns:

        cursor.execute("""
            ALTER TABLE employees
            ADD COLUMN role TEXT DEFAULT 'Employee'
        """)

    if "active" not in employee_columns:

        cursor.execute("""
            ALTER TABLE employees
            ADD COLUMN active INTEGER DEFAULT 1
        """)

    # Refresh employee columns

    cursor.execute(
        "PRAGMA table_info(employees)"
    )

    employee_columns = [
        row["name"]
        for row in cursor.fetchall()
    ]

    # ========================================================
    # OLD EMPLOYEE DATA MIGRATION
    # ========================================================

    if "full_name" in employee_columns:

        cursor.execute("""
            UPDATE employees

            SET employee_name = full_name

            WHERE
                (employee_name IS NULL
                OR employee_name = '')

                AND full_name IS NOT NULL
        """)

    if "employee_id" in employee_columns:

        cursor.execute("""
            UPDATE employees

            SET username = employee_id

            WHERE
                (username IS NULL
                OR username = '')

                AND employee_id IS NOT NULL
        """)

    cursor.execute("""
        UPDATE employees

        SET role = 'Employee'

        WHERE role IS NULL
        OR role = ''
    """)

    cursor.execute("""
        UPDATE employees

        SET active = 1

        WHERE active IS NULL
    """)

    # ========================================================
    # UNIQUE USERNAME INDEX
    # ========================================================

    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS
        idx_employees_username
        ON employees(username)
        WHERE username IS NOT NULL
    """)

    # ========================================================
    # BILL ITEMS TABLE
    #
    # We keep brand_name/salts here for compatibility with
    # older bill records, but values come from the new
    # medicines.medicine_name/generic_name columns.
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bill_items (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            bill_id INTEGER NOT NULL,

            medicine_id INTEGER,

            brand_name TEXT NOT NULL,

            salts TEXT,

            price REAL NOT NULL,

            FOREIGN KEY (bill_id)
                REFERENCES bills(id)

        )
    """)

    # ========================================================
    # DEFAULT USERS
    # ========================================================

    default_users = [

        (
            "Pharmacy Manager",
            "manager1",
            "manager123",
            "Manager"
        ),

        (
            "Pharmacist One",
            "pharmacist1",
            "pass123",
            "Pharmacist"
        ),

        (
            "Pharmacist Two",
            "pharmacist2",
            "pass456",
            "Pharmacist"
        ),

        (
            "Pharmacist Three",
            "pharmacist3",
            "pass789",
            "Pharmacist"
        ),

        (
            "Pharmacy Employee",
            "employee1",
            "employee123",
            "Employee"
        )

    ]

    # ========================================================
    # ADD DEFAULT USERS
    # ========================================================

    for user in default_users:

        employee_name = user[0]
        username = user[1]
        password = user[2]
        role = user[3]

        existing = cursor.execute(
            """
            SELECT id

            FROM employees

            WHERE username = ?

            """,
            (username,)
        ).fetchone()

        if existing:

            continue

        password_hash = generate_password_hash(
            password
        )

        insert_columns = []
        insert_values = []

        if "employee_name" in employee_columns:

            insert_columns.append(
                "employee_name"
            )

            insert_values.append(
                employee_name
            )

        if "full_name" in employee_columns:

            insert_columns.append(
                "full_name"
            )

            insert_values.append(
                employee_name
            )

        if "username" in employee_columns:

            insert_columns.append(
                "username"
            )

            insert_values.append(
                username
            )

        if "employee_id" in employee_columns:

            insert_columns.append(
                "employee_id"
            )

            insert_values.append(
                username
            )

        if "password" in employee_columns:

            insert_columns.append(
                "password"
            )

            insert_values.append(
                password_hash
            )

        if "role" in employee_columns:

            insert_columns.append(
                "role"
            )

            insert_values.append(
                role
            )

        if "active" in employee_columns:
            insert_columns.append(
                "active"
            )

            insert_values.append(
                1
            )

        # ========================================================
        # CREATED AT
        # ========================================================

        if "created_at" in employee_columns:
            insert_columns.append(
                "created_at"
            )

            insert_values.append(
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )

        placeholders = ",".join(
            ["?"] * len(insert_values)
        )

        column_string = ",".join(
            insert_columns
        )

        cursor.execute(
            f"""
            INSERT INTO employees
            ({column_string})

            VALUES ({placeholders})
            """,
            insert_values
        )

    # ========================================================
    # DEFAULT MEDICINES
    #
    # YOUR DATABASE COLUMNS:
    #
    # medicine_name
    # generic_name
    # quantity
    # price
    # created_at
    # ========================================================

    cursor.execute(
        "PRAGMA table_info(medicines)"
    )

    medicine_columns = [
        row["name"]
        for row in cursor.fetchall()
    ]

    default_medicines = [

        (
            "Dolo 650",
            "Paracetamol",
            100,
            30
        ),

        (
            "Crocin",
            "Paracetamol",
            100,
            35
        ),

        (
            "Brufen",
            "Ibuprofen",
            100,
            40
        ),

        (
            "Combiflam",
            "Ibuprofen+Paracetamol",
            100,
            50
        ),

        (
            "Augmentin",
            "Amoxicillin+Clavulanic Acid",
            100,
            120
        ),

        (
            "Azithral",
            "Azithromycin",
            100,
            80
        ),

        (
            "Allegra",
            "Fexofenadine",
            100,
            90
        ),

        (
            "Pantop",
            "Pantoprazole",
            100,
            60
        ),

        (
            "Warfarin",
            "Warfarin",
            100,
            100
        )

    ]

    # --------------------------------------------------------
    # Only insert default medicines if the current table has
    # the medicine_name structure shown by your database.
    # --------------------------------------------------------

    if (
        "medicine_name" in medicine_columns
        and "generic_name" in medicine_columns
        and "price" in medicine_columns
    ):

        for medicine in default_medicines:

            medicine_name = medicine[0]
            generic_name = medicine[1]
            quantity = medicine[2]
            price = medicine[3]

            existing = cursor.execute(
                """
                SELECT id

                FROM medicines

                WHERE medicine_name = ?

                """,
                (medicine_name,)
            ).fetchone()

            if not existing:

                if "created_at" in medicine_columns:

                    cursor.execute("""
                        INSERT INTO medicines
                        (
                            medicine_name,
                            generic_name,
                            quantity,
                            price,
                            created_at
                        )

                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        medicine_name,
                        generic_name,
                        quantity,
                        price,
                        datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                    ))

                else:

                    cursor.execute("""
                        INSERT INTO medicines
                        (
                            medicine_name,
                            generic_name,
                            quantity,
                            price
                        )

                        VALUES (?, ?, ?, ?)
                    """, (
                        medicine_name,
                        generic_name,
                        quantity,
                        price
                    ))

    # ========================================================
    # DEFAULT INTERACTIONS
    # ========================================================

    interactions = [

        (
            "Ibuprofen",
            "Paracetamol",
            "Moderate",
            "Use together only under appropriate medical guidance."
        ),

        (
            "Ibuprofen",
            "Warfarin",
            "Severe",
            "Potentially serious bleeding risk. Pharmacist review required."
        ),

        (
            "Azithromycin",
            "Warfarin",
            "Severe",
            "May increase bleeding risk. Pharmacist review required."
        ),

        (
            "Amoxicillin",
            "Warfarin",
            "Moderate",
            "Monitor patient and review prescription."
        )

    ]

    for interaction in interactions:

        existing = cursor.execute(
            """
            SELECT id

            FROM interactions

            WHERE
                salt1 = ?
                AND salt2 = ?

            """,
            (
                interaction[0],
                interaction[1]
            )
        ).fetchone()

        if not existing:

            cursor.execute("""
                INSERT INTO interactions
                (
                    salt1,
                    salt2,
                    severity,
                    warning
                )

                VALUES (?, ?, ?, ?)
            """, interaction)

    conn.commit()

    conn.close()


# ============================================================
# MEDICINE SELECT HELPER
#
# This converts your actual database columns:
#
# medicine_name
# generic_name
#
# into convenient aliases:
#
# name
# salts
#
# This also keeps your existing HTML working.
# ============================================================

def get_medicines():

    conn = get_db()

    medicines = conn.execute("""
        SELECT

            id,

            medicine_name,

            medicine_name AS name,

            generic_name,

            generic_name AS salts,

            quantity,

            price

        FROM medicines

        ORDER BY medicine_name
    """).fetchall()

    conn.close()

    return medicines


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        if not username or not password:

            return render_template(
                "login.html",
                error="Please enter username and password."
            )

        conn = get_db()

        employee = conn.execute(
            """
            SELECT *

            FROM employees

            WHERE username = ?

            AND active = 1
            """,
            (username,)
        ).fetchone()

        if not employee:

            conn.close()

            return render_template(
                "login.html",
                error="Invalid username or password."
            )

        stored_password = employee["password"]

        valid_password = False

        # ====================================================
        # HASHED PASSWORD
        # ====================================================

        if stored_password:

            try:

                valid_password = check_password_hash(
                    stored_password,
                    password
                )

            except ValueError:

                valid_password = False

        # ====================================================
        # OLD PLAIN TEXT PASSWORD SUPPORT
        # ====================================================

        if (
            not valid_password
            and stored_password == password
        ):

            valid_password = True

            new_hash = generate_password_hash(
                password
            )

            conn.execute(
                """
                UPDATE employees

                SET password = ?

                WHERE id = ?
                """,
                (
                    new_hash,
                    employee["id"]
                )
            )

            conn.commit()

        if not valid_password:

            conn.close()

            return render_template(
                "login.html",
                error="Invalid username or password."
            )

        # ====================================================
        # LOGIN SUCCESS
        # ====================================================

        session.clear()

        session["employee_id"] = employee["id"]

        session["username"] = employee["username"]

        session["employee_name"] = (
            employee["employee_name"]
            or employee["username"]
        )

        session["role"] = (
            employee["role"]
            or "Employee"
        )

        conn.close()

        return redirect(
            url_for("home")
        )

    return render_template(
        "login.html"
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# ============================================================
# HOME
# ============================================================

@app.route("/")
@login_required
def home():

    medicines = get_medicines()

    return render_template(
        "index.html",

        medicines=medicines,

        employee_name=session.get(
            "employee_name"
        ),

        role=session.get(
            "role"
        ),

        username=session.get(
            "username"
        )
    )


# ============================================================
# PRESCRIPTION & BILLING PAGE
# ============================================================

@app.route(
    "/prescription-billing"
)
@login_required
def prescription_billing():

    medicines = get_medicines()

    return render_template(
        "prescription_billing.html",

        medicines=medicines,

        employee_name=session.get(
            "employee_name"
        ),

        role=session.get(
            "role"
        ),

        username=session.get(
            "username"
        )
    )


# ============================================================
# CHECK DRUG INTERACTIONS
# ============================================================

@app.route(
    "/check-interactions",
    methods=["POST"]
)
@login_required
def check_interactions():

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({
            "success": False,
            "message": "Invalid request."
        }), 400

    selected_ids = data.get(
        "medicine_ids",
        []
    )

    if not selected_ids:

        return jsonify({
            "success": False,
            "message":
                "Please select at least one medicine."
        })

    # Make sure IDs are integers

    try:

        selected_ids = [
            int(value)
            for value in selected_ids
        ]

    except (
        ValueError,
        TypeError
    ):

        return jsonify({
            "success": False,
            "message":
                "Invalid medicine selection."
        }), 400

    conn = get_db()

    placeholders = ",".join(
        ["?"] * len(selected_ids)
    )

    medicines = conn.execute(
        f"""
        SELECT

            id,

            medicine_name,

            medicine_name AS name,

            generic_name,

            generic_name AS salts,

            quantity,

            price

        FROM medicines

        WHERE id IN ({placeholders})

        ORDER BY medicine_name
        """,
        selected_ids
    ).fetchall()

    if not medicines:

        conn.close()

        return jsonify({
            "success": False,
            "message":
                "Selected medicines were not found."
        })

    # ========================================================
    # COLLECT GENERIC NAMES / SALTS
    # ========================================================

    all_salts = []

    for medicine in medicines:

        generic_name = (
            medicine["generic_name"]
            or ""
        )

        salts = generic_name.split("+")

        for salt in salts:

            salt = salt.strip()

            if salt and salt not in all_salts:

                all_salts.append(
                    salt
                )

    # ========================================================
    # FIND INTERACTIONS
    # ========================================================

    interactions_found = []

    for i in range(
        len(all_salts)
    ):

        for j in range(
            i + 1,
            len(all_salts)
        ):

            salt1 = all_salts[i]

            salt2 = all_salts[j]

            interaction = conn.execute(
                """
                SELECT *

                FROM interactions

                WHERE

                    (
                        salt1 = ?
                        AND salt2 = ?
                    )

                    OR

                    (
                        salt1 = ?
                        AND salt2 = ?
                    )

                """,
                (
                    salt1,
                    salt2,
                    salt2,
                    salt1
                )
            ).fetchone()

            if interaction:

                interactions_found.append({

                    "salt1":
                        interaction["salt1"],

                    "salt2":
                        interaction["salt2"],

                    "severity":
                        interaction["severity"],

                    "warning":
                        interaction["warning"]

                })

    conn.close()

    # ========================================================
    # DETERMINE STATUS
    # ========================================================

    severe_found = any(

        item["severity"].lower()
        == "severe"

        for item
        in interactions_found

    )

    if severe_found:

        status = "BLOCKED"

    elif interactions_found:

        status = "REVIEW"

    else:

        status = "APPROVED"

    # ========================================================
    # RESPONSE
    # ========================================================

    return jsonify({

        "success": True,

        "status": status,

        "medicines": [

            {

                "id":
                    medicine["id"],

                "name":
                    medicine["medicine_name"],

                "brand_name":
                    medicine["medicine_name"],

                "generic_name":
                    medicine["generic_name"],

                "salts":
                    medicine["generic_name"],

                "quantity":
                    medicine["quantity"],

                "price":
                    medicine["price"]

            }

            for medicine
            in medicines

        ],

        "salts":
            all_salts,

        "interactions":
            interactions_found

    })


# ============================================================
# GENERATE BILL
# ============================================================

@app.route(
    "/generate-bill",
    methods=["POST"]
)
@login_required
def generate_bill():

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({
            "success": False,
            "message": "Invalid request."
        }), 400

    patient_name = data.get(
        "patient_name",
        ""
    ).strip()

    prescription_number = data.get(
        "prescription_number",
        ""
    ).strip()

    medicine_ids = data.get(
        "medicine_ids",
        []
    )

    status = data.get(
        "status",
        "APPROVED"
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    if not patient_name:

        return jsonify({
            "success": False,
            "message":
                "Patient name is required."
        })

    if not prescription_number:

        return jsonify({
            "success": False,
            "message":
                "Prescription number is required."
        })

    if not medicine_ids:

        return jsonify({
            "success": False,
            "message":
                "Please select at least one medicine."
        })

    if status == "BLOCKED":

        return jsonify({
            "success": False,
            "message":
                "Sale is blocked because a severe interaction was detected."
        })

    # ========================================================
    # CONVERT MEDICINE IDs
    # ========================================================

    try:

        medicine_ids = [
            int(value)
            for value in medicine_ids
        ]

    except (
        ValueError,
        TypeError
    ):

        return jsonify({
            "success": False,
            "message":
                "Invalid medicine selection."
        }), 400

    conn = get_db()

    # ========================================================
    # GET SELECTED MEDICINES
    #
    # IMPORTANT:
    #
    # Uses the REAL database columns:
    #
    # medicine_name
    # generic_name
    # price
    # ========================================================

    placeholders = ",".join(
        ["?"] * len(medicine_ids)
    )

    medicines = conn.execute(
        f"""
        SELECT

            id,

            medicine_name,

            generic_name,

            quantity,

            price

        FROM medicines

        WHERE id IN ({placeholders})

        ORDER BY medicine_name
        """,
        medicine_ids
    ).fetchall()

    if not medicines:

        conn.close()

        return jsonify({
            "success": False,
            "message":
                "Selected medicines were not found."
        })

    # ========================================================
    # CALCULATE TOTAL FROM DATABASE
    #
    # We deliberately calculate the total here rather than
    # trusting the value sent by JavaScript.
    # ========================================================

    total_amount = 0

    for medicine in medicines:

        price = medicine["price"] or 0

        total_amount += float(price)

    # ========================================================
    # DATE AND EXACT TIME
    # ========================================================

    now = datetime.now()

    bill_date = now.strftime(
        "%d-%m-%Y %H:%M:%S"
    )

    # ========================================================
    # INSERT BILL
    # ========================================================

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO bills
        (
            patient_name,
            bill_date,
            total_amount,
            status,
            prescription_number,
            employee_id
        )

        VALUES (?, ?, ?, ?, ?, ?)

        """,
        (
            patient_name,
            bill_date,
            total_amount,
            status,
            prescription_number,
            session["employee_id"]
        )
    )

    bill_id = cursor.lastrowid

    # ========================================================
    # INSERT BILL ITEMS
    #
    # Your medicines table calls these:
    #
    # medicine_name
    # generic_name
    #
    # bill_items still uses:
    #
    # brand_name
    # salts
    #
    # so we store the correct values in those columns.
    # ========================================================

    for medicine in medicines:

        cursor.execute(
            """
            INSERT INTO bill_items
            (
                bill_id,
                medicine_id,
                brand_name,
                salts,
                price
            )

            VALUES (?, ?, ?, ?, ?)

            """,
            (
                bill_id,

                medicine["id"],

                medicine["medicine_name"],

                medicine["generic_name"],

                medicine["price"] or 0
            )
        )

    conn.commit()

    conn.close()

    # ========================================================
    # SUCCESS RESPONSE
    # ========================================================

    return jsonify({

        "success": True,

        "bill_id":
            bill_id,

        "patient_name":
            patient_name,

        "prescription_number":
            prescription_number,

        "date":
            bill_date,

        "total":
            total_amount,

        "status":
            status,

        "employee_name":
            session.get(
                "employee_name"
            ),

        "employee_username":
            session.get(
                "username"
            ),

        "medicines": [

            {

                "name":
                    medicine["medicine_name"],

                "brand_name":
                    medicine["medicine_name"],

                "generic_name":
                    medicine["generic_name"],

                "salts":
                    medicine["generic_name"],

                "price":
                    medicine["price"]

            }

            for medicine
            in medicines

        ]

    })


# ============================================================
# BILL PAGE
# ============================================================

@app.route(
    "/bill/<int:bill_id>"
)
@login_required
def bill_page(bill_id):

    conn = get_db()

    bill_data = conn.execute(
        """
        SELECT

            bills.*,

            employees.employee_name,

            employees.username,

            employees.role

        FROM bills

        LEFT JOIN employees

        ON bills.employee_id =
           employees.id

        WHERE bills.id = ?

        """,
        (bill_id,)
    ).fetchone()

    if not bill_data:

        conn.close()

        return "Bill not found.", 404

    bill_items = conn.execute(
        """
        SELECT *

        FROM bill_items

        WHERE bill_id = ?

        ORDER BY id

        """,
        (bill_id,)
    ).fetchall()

    conn.close()

    bill = {

        "bill_id":
            bill_data["id"],

        "date":
            bill_data["bill_date"],

        "patient_name":
            bill_data["patient_name"],

        "prescription_number":
            bill_data["prescription_number"],

        "total":
            bill_data["total_amount"],

        "status":
            bill_data["status"],

        "employee_name":
            bill_data["employee_name"],

        "employee_username":
            bill_data["username"],

        "employee_role":
            bill_data["role"],

        "medicines": [

            {

                "name":
                    item["brand_name"],

                "brand_name":
                    item["brand_name"],

                "salts":
                    item["salts"],

                "generic_name":
                    item["salts"],

                "price":
                    item["price"]

            }

            for item
            in bill_items

        ]

    }

    return render_template(
        "bill.html",
        bill=bill
    )


# ============================================================
# BILL HISTORY
# ============================================================

@app.route(
    "/bill-history"
)
@login_required
def bill_history():

    conn = get_db()

    # ========================================================
    # MANAGER SEES ALL BILLS
    # ========================================================

    if session.get("role") == "Manager":

        bills = conn.execute(
            """
            SELECT

                bills.id,

                bills.patient_name,

                bills.bill_date,

                bills.total_amount,

                bills.status,

                bills.prescription_number,

                employees.employee_name,

                employees.username,

                employees.role

            FROM bills

            LEFT JOIN employees

            ON bills.employee_id =
               employees.id

            ORDER BY bills.id DESC

            """
        ).fetchall()

    # ========================================================
    # OTHER EMPLOYEES SEE THEIR OWN BILLS
    # ========================================================

    else:

        bills = conn.execute(
            """
            SELECT

                bills.id,

                bills.patient_name,

                bills.bill_date,

                bills.total_amount,

                bills.status,

                bills.prescription_number,

                employees.employee_name,

                employees.username,

                employees.role

            FROM bills

            LEFT JOIN employees

            ON bills.employee_id =
               employees.id

            WHERE bills.employee_id = ?

            ORDER BY bills.id DESC

            """,
            (
                session["employee_id"],
            )
        ).fetchall()

    conn.close()

    return render_template(
        "bill_history.html",

        bills=bills,

        employee_name=session.get(
            "employee_name"
        ),

        role=session.get(
            "role"
        )
    )


# ============================================================
# ADD NEW EMPLOYEE
# ============================================================

@app.route(
    "/add-employee",
    methods=["GET", "POST"]
)
@manager_required
def add_employee():

    # ========================================================
    # SHOW PAGE
    # ========================================================

    if request.method == "GET":

        return render_template(
            "add_employee.html"
        )

    # ========================================================
    # GET DATA
    # ========================================================

    if request.is_json:

        data = request.get_json(
            silent=True
        ) or {}

    else:

        data = request.form

    employee_name = data.get(
        "employee_name",
        ""
    ).strip()

    username = data.get(
        "username",
        ""
    ).strip()

    password = data.get(
        "password",
        ""
    )

    role = data.get(
        "role",
        "Employee"
    ).strip()

    # ========================================================
    # VALID ROLES
    # ========================================================

    allowed_roles = [
        "Employee",
        "Pharmacist",
        "Manager"
    ]

    if role not in allowed_roles:

        role = "Employee"

    # ========================================================
    # VALIDATION
    # ========================================================

    if not employee_name:

        return jsonify({
            "success": False,
            "message":
                "Employee name is required."
        })

    if not username:

        return jsonify({
            "success": False,
            "message":
                "Username is required."
        })

    if not password:

        return jsonify({
            "success": False,
            "message":
                "Password is required."
        })

    if len(password) < 6:

        return jsonify({
            "success": False,
            "message":
                "Password must contain at least 6 characters."
        })

    conn = get_db()

    existing = conn.execute(
        """
        SELECT id

        FROM employees

        WHERE username = ?

        """,
        (username,)
    ).fetchone()

    if existing:

        conn.close()

        return jsonify({
            "success": False,
            "message":
                "Username already exists."
        })

    password_hash = generate_password_hash(
        password
    )

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO employees
        (
            employee_name,
            username,
            password,
            role,
            active
        )

        VALUES (?, ?, ?, ?, 1)

        """,
        (
            employee_name,
            username,
            password_hash,
            role
        )
    )

    new_employee_id = cursor.lastrowid

    conn.commit()

    conn.close()

    return jsonify({

        "success": True,

        "message":
            "Employee created successfully.",

        "employee_id":
            new_employee_id,

        "employee_name":
            employee_name,

        "username":
            username,

        "role":
            role

    })


# ============================================================
# VIEW EMPLOYEES
# ============================================================

@app.route(
    "/employees"
)
@manager_required
def employees():

    conn = get_db()

    employee_list = conn.execute(
        """
        SELECT

            id,

            employee_name,

            username,

            role,

            active

        FROM employees

        ORDER BY employee_name

        """
    ).fetchall()

    conn.close()

    return render_template(
        "employees.html",
        employees=employee_list
    )


# ============================================================
# CHANGE PASSWORD
# ============================================================

@app.route(
    "/change-password",
    methods=["GET", "POST"]
)
@login_required
def change_password():

    if request.method == "GET":

        return render_template(
            "change_password.html"
        )

    if request.is_json:

        data = request.get_json(
            silent=True
        ) or {}

    else:

        data = request.form

    current_password = data.get(
        "current_password",
        ""
    )

    new_password = data.get(
        "new_password",
        ""
    )

    confirm_password = data.get(
        "confirm_password",
        ""
    )

    if not current_password:

        return jsonify({
            "success": False,
            "message":
                "Current password is required."
        })

    if not new_password:

        return jsonify({
            "success": False,
            "message":
                "New password is required."
        })

    if new_password != confirm_password:

        return jsonify({
            "success": False,
            "message":
                "New passwords do not match."
        })

    if len(new_password) < 6:

        return jsonify({
            "success": False,
            "message":
                "New password must contain at least 6 characters."
        })

    conn = get_db()

    employee = conn.execute(
        """
        SELECT *

        FROM employees

        WHERE id = ?

        """,
        (
            session["employee_id"],
        )
    ).fetchone()

    if not employee:

        conn.close()

        session.clear()

        return redirect(
            url_for("login")
        )

    password_valid = False

    try:

        password_valid = check_password_hash(
            employee["password"],
            current_password
        )

    except (
        ValueError,
        TypeError
    ):

        password_valid = (
            employee["password"]
            == current_password
        )

    if not password_valid:

        conn.close()

        return jsonify({
            "success": False,
            "message":
                "Current password is incorrect."
        })

    new_password_hash = generate_password_hash(
        new_password
    )

    conn.execute(
        """
        UPDATE employees

        SET password = ?

        WHERE id = ?

        """,
        (
            new_password_hash,
            session["employee_id"]
        )
    )

    conn.commit()

    conn.close()

    return jsonify({

        "success": True,

        "message":
            "Password changed successfully."

    })


# ============================================================
# MANAGER RESET PASSWORD
# ============================================================

@app.route(
    "/manager-reset-password",
    methods=["POST"]
)
@manager_required
def manager_reset_password():

    if request.is_json:

        data = request.get_json(
            silent=True
        ) or {}

    else:

        data = request.form

    username = data.get(
        "username",
        ""
    ).strip()

    new_password = data.get(
        "new_password",
        ""
    )

    if not username:

        return jsonify({
            "success": False,
            "message":
                "Username is required."
        })

    if len(new_password) < 6:

        return jsonify({
            "success": False,
            "message":
                "Password must contain at least 6 characters."
        })

    conn = get_db()

    employee = conn.execute(
        """
        SELECT id

        FROM employees

        WHERE username = ?

        """,
        (username,)
    ).fetchone()

    if not employee:

        conn.close()

        return jsonify({
            "success": False,
            "message":
                "User not found."
        })

    password_hash = generate_password_hash(
        new_password
    )

    conn.execute(
        """
        UPDATE employees

        SET password = ?

        WHERE id = ?

        """,
        (
            password_hash,
            employee["id"]
        )
    )

    conn.commit()

    conn.close()

    return jsonify({

        "success": True,

        "message":
            "User password has been reset successfully."

    })


# ============================================================
# MANAGER DASHBOARD
# ============================================================

@app.route(
    "/manager-dashboard"
)
@manager_required
def manager_dashboard():

    conn = get_db()

    total_users = conn.execute(
        """
        SELECT COUNT(*)

        FROM employees

        WHERE active = 1

        """
    ).fetchone()[0]

    total_bills = conn.execute(
        """
        SELECT COUNT(*)

        FROM bills

        """
    ).fetchone()[0]

    total_sales = conn.execute(
        """
        SELECT COALESCE(
            SUM(total_amount),
            0
        )

        FROM bills

        WHERE status != 'BLOCKED'

        """
    ).fetchone()[0]

    conn.close()

    return render_template(
        "manager_dashboard.html",

        total_users=total_users,

        total_bills=total_bills,

        total_sales=total_sales
    )


# ============================================================
# APPLICATION START
# ============================================================

if __name__ == "__main__":

    initialize_database()

    app.run(
        debug=True
    )