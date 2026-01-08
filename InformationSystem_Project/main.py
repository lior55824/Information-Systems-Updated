from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta
from utils import *
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
app.secret_key = "flytau_project_secret_key_2025!"

# -----------------------------
# DB Connection
# -----------------------------
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="NoaKopilo7712!",
        database="FLYTAU"
    )


@app.route("/db-check")
def db_check():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT DATABASE() AS db;")
        db = cursor.fetchone()["db"]

        cursor.execute("SHOW TABLES;")
        tables = [row[f"Tables_in_{db}"] for row in cursor.fetchall()]

        cursor.execute("SELECT COUNT(*) AS cnt FROM Airports;")
        airports_cnt = cursor.fetchone()["cnt"]

        return {"ok": True, "database": db, "tables_count": len(tables), "airports_count": airports_cnt}

    except Exception as e:
        return {"ok": False, "error": str(e)}, 500

    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except:
            pass


@app.errorhandler(404)
def invalid_route(e):
    return redirect("/")


# =============================
# HOME
# =============================
@app.route('/')
def home_page():
    selected_origin = request.args.get("origin_id")          # מגיע מה-URL כטקסט
    selected_destination = request.args.get("destination_id")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    today = datetime.now().date().isoformat()

    conn = None
    cursor = None
    airports = []

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT Airport_ID, Airport_Name, City, Country
            FROM Airports
            ORDER BY Country, City, Airport_Name
        """)
        airports = cursor.fetchall()

    except Exception as e:
        flash(f"Database error loading airports: {e}", "error")

    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except:
            pass

    return render_template(
        "home_page.html",
        airports=airports,
        selected_origin=selected_origin,
        selected_destination=selected_destination,
        start_date=start_date,
        end_date=end_date,
        today=today
    )


# =============================
# LOGIN (Client + Admin in one page)
# =============================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    user_type = request.form.get("user_type", "client")  # client/admin
    password = request.form.get("Password", "")

    if not password:
        flash("Please enter password.", "error")
        return render_template("login.html")

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # ------------------ ADMIN LOGIN ------------------
        if user_type == "admin":
            worker_id = request.form.get("Worker_ID", "").strip()

            if not worker_id:
                flash("Please enter Worker ID.", "error")
                return render_template("login.html", Worker_ID=worker_id, Email_Address="")

            cursor.execute("""
                SELECT Worker_ID, Manager_Password, Manager_First_Name_In_English
                FROM Managers
                WHERE Worker_ID = %s
            """, (worker_id,))
            admin = cursor.fetchone()

            if not admin or admin.get("Manager_Password") != password:
                flash("Invalid Worker ID or password.", "error")
                return render_template("login.html", Worker_ID=worker_id, Email_Address="")

            session.clear()
            session["user_type"] = "admin"
            session["worker_id"] = admin["Worker_ID"]
            session["admin_name"] = admin.get("Manager_First_Name_In_English", "Admin")

            return redirect(url_for("admin_dashboard"))

        # ------------------ CLIENT LOGIN ------------------
        # ✅ תיקון לסכמה שלך: Registered_Clients_Email_Address
        email = request.form.get("Email_Address", "").strip()

        if not email:
            flash("Please enter Email Address.", "error")
            return render_template("login.html", Email_Address=email, Worker_ID="")

        cursor.execute("""
            SELECT Registered_Clients_Email_Address AS Email_Address,
                   Client_Password,
                   First_Name_In_English
            FROM Registered_Clients
            WHERE Registered_Clients_Email_Address = %s
        """, (email,))
        client = cursor.fetchone()

        if not client or client.get("Client_Password") != password:
            flash("Invalid email or password.", "error")
            return render_template("login.html", Email_Address=email, Worker_ID="")

        session.clear()
        session["user_type"] = "registered_client"
        session["Email_Address"] = client["Email_Address"]
        session["First_Name_In_English"] = client.get("First_Name_In_English", "")

        return redirect(url_for("client_home"))

    except Exception:
        flash("Database error.", "error")
        return render_template("login.html")

    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass


@app.route("/client_home")
def client_home():
    if session.get("user_type") != "registered_client":
        return redirect(url_for("login"))
    return f"Welcome {session.get('First_Name_In_English', '')}!"


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# =============================
# REGISTER
# =============================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html", datetime=datetime)

    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    email = request.form.get("email", "").strip()
    passport_id = request.form.get("passport_id", "").strip()
    birth_date = request.form.get("birth_date", "").strip()
    password = request.form.get("password", "")

    if not all([first_name, last_name, email, passport_id, birth_date, password]):
        flash("Please fill in all fields.", "error")
        return render_template("register.html", datetime=datetime)

    # אם תרצי: נוכל להפוך את זה ל-insert אמיתי עם בדיקת אימייל קיים.
    flash("Account created (temporary, not saved yet). Please login.", "success")
    return redirect(url_for("login"))


# =============================
# GUEST SEARCH
# =============================
@app.route('/guest/search')
def guest_search():
    return render_template('guest_search.html')


# =============================
# AVAILABLE FLIGHTS
# =============================
@app.route("/available-flights")
def available_flights():
    origin_id = (request.args.get("origin_id") or "").strip()
    destination_id = (request.args.get("destination_id") or "").strip()
    start_date = (request.args.get("start_date") or "").strip()
    end_date = (request.args.get("end_date") or "").strip()

    if not origin_id and not destination_id and not start_date and not end_date:
        flash("Please search first.", "error")
        return redirect(url_for("home_page"))

    conn = None
    cursor = None
    airports = []
    flights = []

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT Airport_ID, Airport_Name, City, Country
            FROM Airports
            ORDER BY Country, City, Airport_Name
        """)
        airports = cursor.fetchall()

        sql = """
            SELECT
                f.Flight_ID,
                f.Departure_Date,
                f.Departure_Time,
                f.Economy_Price,
                f.Bussines_Price,

                ao.Airport_Name AS origin_airport_name,
                ao.City AS origin_city,
                ao.Country AS origin_country,

                ad.Airport_Name AS dest_airport_name,
                ad.City AS dest_city,
                ad.Country AS dest_country
            FROM Flight f
            JOIN Airports ao ON ao.Airport_ID = f.Origin_Airport
            JOIN Airports ad ON ad.Airport_ID = f.Destination_Airport
            WHERE 1=1
        """
        params = []

        if origin_id:
            sql += " AND f.Origin_Airport = %s"
            params.append(origin_id)

        if destination_id:
            sql += " AND f.Destination_Airport = %s"
            params.append(destination_id)

        if start_date and end_date:
            sql += " AND f.Departure_Date BETWEEN %s AND %s"
            params.extend([start_date, end_date])
        elif start_date:
            sql += " AND f.Departure_Date >= %s"
            params.append(start_date)
        elif end_date:
            sql += " AND f.Departure_Date <= %s"
            params.append(end_date)

        sql += " ORDER BY f.Departure_Date, f.Departure_Time"

        cursor.execute(sql, tuple(params))
        flights = cursor.fetchall()

    except Exception as e:
        flash(f"Database error loading flights: {e}", "error")
        flights = []

    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass

    return render_template(
        "available_flights.html",
        airports=airports,
        flights=flights,
        origin_id=origin_id,
        destination_id=destination_id,
        start_date=start_date,
        end_date=end_date
    )


# =============================
# BOOK FLIGHT + ORDER SUMMARY
# =============================

def next_order_id(cursor) -> int:
    cursor.execute("SELECT COALESCE(MAX(Unique_Order_ID), 9000) + 1 AS next_id FROM Orders")
    return int(cursor.fetchone()["next_id"])

@app.route("/draft/select-seats", methods=["GET", "POST"])
def draft_select_seats():
    draft = session.get("draft_order")
    if not draft:
        flash("Please start a booking first.", "error")
        return redirect(url_for("home_page"))

    flight_id = int(draft["flight_id"])
    plane_id = int(draft["plane_id"])
    needed = int(draft["quantity"])

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # all seats in plane
        cursor.execute("""
            SELECT Row_Num, Column_Number, Class
            FROM Seats
            WHERE Plane_ID = %s
            ORDER BY Row_Num, Column_Number
        """, (plane_id,))
        all_seats = cursor.fetchall()

        # occupied seats in THIS flight by existing orders
        cursor.execute("""
            SELECT ss.Row_Num, ss.Column_Number
            FROM Selected_Seats ss
            JOIN Orders o ON o.Unique_Order_ID = ss.Unique_Order_ID
            WHERE o.Flight_ID = %s
              AND ss.Plane_ID = %s
              AND ss.Is_Occupied = 1
        """, (flight_id, plane_id))
        occ_rows = cursor.fetchall()
        occupied = {f"{r['Row_Num']}{r['Column_Number']}" for r in occ_rows}

        selected_prev = set(session.get("draft_selected_seats", []))

        if request.method == "POST":
            selected = request.form.getlist("seat_choice")

            if len(selected) != needed:
                flash(f"Please select exactly {needed} seats.", "error")
                return render_template(
                    "draft_select_seats.html",
                    seats=all_seats,
                    occupied=occupied,
                    selected=selected_prev,
                    needed=needed
                )

            # if someone took seats while user is selecting
            if any(s in occupied for s in selected):
                flash("One or more seats are no longer available. Please choose again.", "error")
                return redirect(url_for("draft_select_seats"))

            session["draft_selected_seats"] = selected
            return redirect(url_for("order_review"))

        return render_template(
            "draft_select_seats.html",
            seats=all_seats,
            occupied=occupied,
            selected=selected_prev,
            needed=needed
        )

    except Exception as e:
        flash(f"Database error while loading seats: {e}", "error")
        return redirect(url_for("home_page"))
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass


@app.route("/draft/review", methods=["GET"])
def order_review():
    draft = session.get("draft_order")
    seats = session.get("draft_selected_seats", [])

    if not draft:
        flash("Please start a booking first.", "error")
        return redirect(url_for("home_page"))

    needed = int(draft["quantity"])
    if not seats or len(seats) != needed:
        flash("Please select seats first.", "error")
        return redirect(url_for("draft_select_seats"))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                f.Flight_ID, f.Departure_Date, f.Departure_Time,
                f.Economy_Price, f.Bussines_Price,
                ao.Airport_Name AS origin_airport_name, ao.City AS origin_city, ao.Country AS origin_country,
                ad.Airport_Name AS dest_airport_name, ad.City AS dest_city, ad.Country AS dest_country
            FROM Flight f
            JOIN Airports ao ON ao.Airport_ID = f.Origin_Airport
            JOIN Airports ad ON ad.Airport_ID = f.Destination_Airport
            WHERE f.Flight_ID = %s
        """, (int(draft["flight_id"]),))
        flight = cursor.fetchone()
        if not flight:
            flash("Flight not found.", "error")
            return redirect(url_for("home_page"))

        # pricing: economy * quantity (אפשר לשדרג בעתיד לפי class)
        total_price = float(flight["Economy_Price"]) * needed

        return render_template(
            "order_review.html",
            draft=draft,
            flight=flight,
            seats=seats,
            total_price=total_price
        )

    except Exception as e:
        flash(f"Database error: {e}", "error")
        return redirect(url_for("home_page"))
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass


@app.route("/draft/confirm", methods=["POST"])
def confirm_order():
    draft = session.get("draft_order")
    seats = session.get("draft_selected_seats", [])

    if not draft or not seats:
        flash("Missing booking data. Please start again.", "error")
        return redirect(url_for("home_page"))

    needed = int(draft["quantity"])
    if len(seats) != needed:
        flash("Seat selection is incomplete.", "error")
        return redirect(url_for("draft_select_seats"))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        flight_id = int(draft["flight_id"])
        plane_id = int(draft["plane_id"])
        email = draft["email"]
        user_type = draft["user_type"]

        # re-check seats are still free (race condition)
        for seat_id in seats:
            row_num = int(seat_id[:-1])
            col = seat_id[-1]
            cursor.execute("""
                SELECT 1
                FROM Selected_Seats ss
                JOIN Orders o ON o.Unique_Order_ID = ss.Unique_Order_ID
                WHERE o.Flight_ID = %s
                  AND ss.Plane_ID = %s
                  AND ss.Row_Num = %s
                  AND ss.Column_Number = %s
                  AND ss.Is_Occupied = 1
                LIMIT 1
            """, (flight_id, plane_id, row_num, col))
            if cursor.fetchone():
                conn.rollback()
                flash("One or more seats were taken while you were booking. Please choose again.", "error")
                return redirect(url_for("draft_select_seats"))

        # upsert guest if needed
        if user_type == "guest":
            cursor.execute("SELECT Email_Address FROM Unidentified_Guests WHERE Email_Address = %s", (email,))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO Unidentified_Guests (Email_Address, First_Name_In_English, Last_Name_In_English)
                    VALUES (%s, %s, %s)
                """, (email, draft.get("first_name", ""), draft.get("last_name", "")))

        # create order id
        new_order_id = next_order_id(cursor)

        # get flight date for Orders.Flight_Date
        cursor.execute("SELECT Departure_Date FROM Flight WHERE Flight_ID = %s", (flight_id,))
        frow = cursor.fetchone()
        if not frow:
            flash("Flight not found.", "error")
            return redirect(url_for("home_page"))
        flight_date = frow["Departure_Date"]

        # insert Orders
        if user_type == "registered_client":
            cursor.execute("""
                INSERT INTO Orders
                  (Unique_Order_ID, Flight_ID, Registered_Clients_Email_Address, Unidentified_Guest_Email_Address,
                   Flight_Date, Order_Status)
                VALUES
                  (%s, %s, %s, NULL, %s, 'Active')
            """, (new_order_id, flight_id, email, flight_date))
        else:
            cursor.execute("""
                INSERT INTO Orders
                  (Unique_Order_ID, Flight_ID, Registered_Clients_Email_Address, Unidentified_Guest_Email_Address,
                   Flight_Date, Order_Status)
                VALUES
                  (%s, %s, NULL, %s, %s, 'Active')
            """, (new_order_id, flight_id, email, flight_date))

        # insert Has_an_order
        cursor.execute("""
            INSERT INTO Has_an_order (Email_Address, Unique_Order_ID, Quantity_of_tickets)
            VALUES (%s, %s, %s)
        """, (email, new_order_id, needed))

        # insert Selected_Seats
        for seat_id in seats:
            row_num = int(seat_id[:-1])
            col = seat_id[-1]
            cursor.execute("""
                INSERT INTO Selected_Seats (Plane_ID, Unique_Order_ID, Column_Number, Row_Num, Is_Occupied)
                VALUES (%s, %s, %s, %s, 1)
            """, (plane_id, new_order_id, col, row_num))

        conn.commit()

        # allow guest to see it later without extra lookup
        if user_type == "guest":
            session["guest_unique_order_id"] = str(new_order_id)
            session["guest_email_address"] = email

        # clear draft session
        session.pop("draft_order", None)
        session.pop("draft_selected_seats", None)

        return redirect(url_for("order_confirmed", unique_order_id=new_order_id))

    except Exception as e:
        try:
            if conn: conn.rollback()
        except Exception:
            pass
        flash(f"Database error while confirming order: {e}", "error")
        return redirect(url_for("order_review"))
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass


@app.route("/order/<int:unique_order_id>/confirmed")
def order_confirmed(unique_order_id):
    user_is_reg, email = get_order_owner_email()
    if not email:
        flash("Order confirmed. Please use Order Management to look it up.", "info")
        return redirect(url_for("order_management", tab="future"))

    order = fetch_order_details(unique_order_id, user_is_reg=user_is_reg, email=email)
    if not order:
        flash("Order not found or access denied.", "error")
        return redirect(url_for("order_management", tab="future"))

    return render_template("order_confirmed.html", order=order)

@app.route("/book/<int:flight_id>", methods=["GET", "POST"])
def book_flight(flight_id):
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                f.Flight_ID, f.Departure_Date, f.Departure_Time,
                f.Economy_Price, f.Bussines_Price,
                f.Plane_ID,
                ao.Airport_Name AS origin_airport_name, ao.City AS origin_city, ao.Country AS origin_country,
                ad.Airport_Name AS dest_airport_name, ad.City AS dest_city, ad.Country AS dest_country
            FROM Flight f
            JOIN Airports ao ON ao.Airport_ID = f.Origin_Airport
            JOIN Airports ad ON ad.Airport_ID = f.Destination_Airport
            WHERE f.Flight_ID = %s
        """, (flight_id,))
        flight = cursor.fetchone()

        if not flight:
            flash("Flight not found.", "error")
            return redirect(url_for("home_page"))

        if request.method == "GET":
            return render_template(
                "book_flight.html",
                flight=flight,
                user_is_registered=is_registered_user()
            )

        # ---------- POST ----------
        quantity_str = (request.form.get("quantity") or "").strip()
        try:
            quantity = int(quantity_str)
            if quantity <= 0:
                raise ValueError()
        except Exception:
            flash("Please enter a valid quantity.", "error")
            return render_template("book_flight.html", flight=flight, user_is_registered=is_registered_user())

        # Registered
        # ---------- POST: SAVE DRAFT IN SESSION (NO DB YET) ----------
        quantity_str = (request.form.get("quantity") or "").strip()
        try:
            quantity = int(quantity_str)
            if quantity <= 0:
                raise ValueError()
        except Exception:
            flash("Please enter a valid quantity.", "error")
            return render_template("book_flight.html", flight=flight, user_is_registered=is_registered_user())

        draft = {
            "flight_id": int(flight_id),
            "plane_id": int(flight["Plane_ID"]),
            "quantity": int(quantity),
            "created_at": datetime.now().isoformat()
        }

        if is_registered_user():
            draft["user_type"] = "registered_client"
            draft["email"] = session.get("Email_Address")
            draft["first_name"] = session.get("First_Name_In_English", "")
            draft["last_name"] = ""
        else:
            guest_email = (request.form.get("guest_email") or "").strip()
            guest_first = (request.form.get("guest_first_name") or "").strip()
            guest_last = (request.form.get("guest_last_name") or "").strip()

            if not guest_email or not guest_first or not guest_last:
                flash("Please fill guest details (email + first/last name).", "error")
                return render_template("book_flight.html", flight=flight, user_is_registered=False)

            draft["user_type"] = "guest"
            draft["email"] = guest_email
            draft["first_name"] = guest_first
            draft["last_name"] = guest_last

        session["draft_order"] = draft
        session["draft_selected_seats"] = []

        return redirect(url_for("draft_select_seats"))

        # Guest
        guest_email = (request.form.get("guest_email") or "").strip()
        guest_first = (request.form.get("guest_first_name") or "").strip()
        guest_last = (request.form.get("guest_last_name") or "").strip()

        if not guest_email or not guest_first or not guest_last:
            flash("Please fill guest details (email + first/last name).", "error")
            return render_template("book_flight.html", flight=flight, user_is_registered=False)

        # upsert guest
        cursor.execute("SELECT Email_Address FROM Unidentified_Guests WHERE Email_Address = %s", (guest_email,))
        exists = cursor.fetchone()
        if not exists:
            cursor.execute("""
                INSERT INTO Unidentified_Guests (Email_Address, First_Name_In_English, Last_Name_In_English)
                VALUES (%s, %s, %s)
            """, (guest_email, guest_first, guest_last))

        new_order_id = next_order_id(cursor)

        cursor.execute("""
            INSERT INTO Orders
              (Unique_Order_ID, Flight_ID, Registered_Clients_Email_Address, Unidentified_Guest_Email_Address,
               Flight_Date, Order_Status)
            VALUES
              (%s, %s, NULL, %s, %s, %s)
        """, (new_order_id, flight_id, guest_email, flight["Departure_Date"], "Active"))

        cursor.execute("""
            INSERT INTO Has_an_order (Email_Address, Unique_Order_ID, Quantity_of_tickets)
            VALUES (%s, %s, %s)
        """, (guest_email, new_order_id, quantity))

        conn.commit()

        # ✅ חשוב: לשמור session כדי ש־select_seats ו־summary יעבדו לאורח
        session["guest_unique_order_id"] = str(new_order_id)
        session["guest_email_address"] = guest_email

        flash("Order created successfully! Now choose seats.", "success")
        return redirect(url_for("select_seats", unique_order_id=new_order_id))

    except Exception as e:
        try:
            if conn:
                conn.rollback()
        except Exception:
            pass
        flash(f"Database error while creating order: {e}", "error")
        return redirect(url_for("book_flight", flight_id=flight_id))

    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass




@app.route("/order/<int:unique_order_id>/summary")
def order_summary(unique_order_id):
    user_is_reg, email = get_order_owner_email()
    if not email:
        flash("Please login or look up your order first.", "error")
        return redirect(url_for("order_management", tab="future"))

    order = fetch_order_details(unique_order_id, user_is_reg=user_is_reg, email=email)
    if not order:
        flash("Order not found or access denied.", "error")
        return redirect(url_for("order_management", tab="future"))

    return render_template("order_summary.html", order=order)


# =============================
# ORDER MANAGEMENT HELPERS
# =============================
def is_registered_user():
    return session.get("user_type") == "registered_client" and session.get("Email_Address")


def get_order_owner_email():
    """
    מחזיר טופל: (user_is_reg, email)
    email יהיה:
      - Registered client: session["Email_Address"]
      - Guest: session["guest_email_address"]
    """
    user_is_reg = bool(is_registered_user())
    if user_is_reg:
        return True, session.get("Email_Address")
    return False, session.get("guest_email_address")


def can_cancel(departure_date, departure_time):
    if not departure_date or not departure_time:
        return False

    d = str(departure_date)
    t = str(departure_time)
    fmt = "%Y-%m-%d %H:%M:%S" if len(t) == 8 else "%Y-%m-%d %H:%M"
    dep_dt = datetime.strptime(f"{d} {t}", fmt)

    return dep_dt >= (datetime.now() + timedelta(hours=36))


# =============================
# ORDER MANAGEMENT
# =============================
@app.route("/order-management")
def order_management():
    tab = request.args.get("tab", "future")
    if tab not in ("future", "history"):
        tab = "future"

    user_is_reg = bool(is_registered_user())
    future_orders, past_orders = [], []

    if tab == "future":
        if user_is_reg:
            email = session.get("Email_Address")
            future_orders = fetch_future_orders_registered(email)
        else:
            # ✅ אורח רואה הזמנה גם אחרי רענון, אם עשה lookup
            unique = session.get("guest_unique_order_id")
            gemail = session.get("guest_email_address")
            if unique and gemail:
                future_orders = fetch_future_orders_guest(unique, gemail)
    else:
        if user_is_reg:
            email = session.get("Email_Address")
            past_orders = fetch_past_orders_registered(email)

    return render_template(
        "order_management.html",
        active_tab=tab,
        user_is_registered=user_is_reg,
        future_orders=future_orders,
        past_orders=past_orders
    )


@app.route("/lookup-order", methods=["POST"])
def lookup_order():
    unique_order_id = request.form.get("unique_order_id", "").strip()
    email_address = request.form.get("email_address", "").strip()

    if not unique_order_id or not email_address:
        flash("Please enter both Order ID and Email Address.", "error")
        return redirect(url_for("order_management", tab="future"))

    session["guest_unique_order_id"] = unique_order_id
    session["guest_email_address"] = email_address

    future_orders = fetch_future_orders_guest(unique_order_id, email_address)
    if not future_orders:
        flash("Order not found or Email Address does not match.", "error")
        return redirect(url_for("order_management", tab="future"))

    return render_template(
        "order_management.html",
        active_tab="future",
        user_is_registered=False,
        future_orders=future_orders,
        past_orders=[]
    )


@app.route("/cancel-order", methods=["POST"])
def cancel_order():
    unique_order_id = request.form.get("unique_order_id", "").strip()
    if not unique_order_id:
        flash("Missing Order ID.", "error")
        return redirect(url_for("order_management", tab="future"))

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # ✅ התאמה לסכמה: עמודות אימייל שונות ל-Registered/Guest
        if is_registered_user():
            email = session.get("Email_Address")

            cursor.execute("""
                SELECT o.Unique_Order_ID,
                       o.Registered_Clients_Email_Address AS Email_Address,
                       o.Order_Status,
                       f.Flight_ID, f.Origin_Airport, f.Destination_Airport,
                       f.Departure_Date, f.Departure_Time
                FROM Orders o
                JOIN Flight f ON f.Flight_ID = o.Flight_ID
                WHERE o.Unique_Order_ID = %s
                  AND o.Registered_Clients_Email_Address = %s
            """, (unique_order_id, email))
            row = cursor.fetchone()

        else:
            guest_email = session.get("guest_email_address")
            guest_order = session.get("guest_unique_order_id")

            if not guest_email or not guest_order:
                flash("Please look up your order first.", "error")
                return redirect(url_for("order_management", tab="future"))

            if str(guest_order) != str(unique_order_id):
                flash("Access denied.", "error")
                return redirect(url_for("order_management", tab="future"))

            cursor.execute("""
                SELECT o.Unique_Order_ID,
                       o.Unidentified_Guest_Email_Address AS Email_Address,
                       o.Order_Status,
                       f.Flight_ID, f.Origin_Airport, f.Destination_Airport,
                       f.Departure_Date, f.Departure_Time
                FROM Orders o
                JOIN Flight f ON f.Flight_ID = o.Flight_ID
                WHERE o.Unique_Order_ID = %s
                  AND o.Unidentified_Guest_Email_Address = %s
            """, (unique_order_id, guest_email))
            row = cursor.fetchone()

        if not row:
            flash("Order not found or access denied.", "error")
            return redirect(url_for("order_management", tab="future"))

        if str(row.get("Order_Status", "")).upper() == "CANCELLED":
            flash("Order is already cancelled.", "info")
            return redirect(url_for("order_management", tab="future"))

        if not can_cancel(row.get("Departure_Date"), row.get("Departure_Time")):
            flash("Cancellation is not available for this order.", "error")
            return redirect(url_for("order_management", tab="future"))

        cursor.execute("""
            UPDATE Orders
            SET Order_Status = 'CANCELLED'
            WHERE Unique_Order_ID = %s
        """, (unique_order_id,))
        conn.commit()

        flash("Order cancelled successfully.", "success")
        return redirect(url_for("order_management", tab="future"))

    except Exception:
        flash("Database error during cancellation.", "error")
        return redirect(url_for("order_management", tab="future"))

    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass


@app.route("/order/<unique_order_id>")
def order_details(unique_order_id):
    user_is_reg, email = get_order_owner_email()
    if not email:
        flash("Please login or look up your order first.", "error")
        return redirect(url_for("order_management", tab="future"))

    order = fetch_order_details(unique_order_id, user_is_reg=user_is_reg, email=email)
    if not order:
        flash("Order not found or access denied.", "error")
        return redirect(url_for("order_management", tab="future"))

    return render_template("order_details.html", order=order)


# =============================
# SELECT SEATS (GET+POST) ✅ חדש
# =============================
@app.route("/order/<unique_order_id>/select-seats", methods=["GET", "POST"])
def select_seats(unique_order_id):
    user_is_reg, email = get_order_owner_email()
    if not email:
        flash("Please login or look up your order first.", "error")
        return redirect(url_for("order_management", tab="future"))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # order + plane_id
        if user_is_reg:
            cursor.execute("""
                SELECT o.Unique_Order_ID, o.Flight_ID, f.Plane_ID,
                       o.Registered_Clients_Email_Address AS Order_Email,
                       o.Order_Status
                FROM Orders o
                JOIN Flight f ON f.Flight_ID = o.Flight_ID
                WHERE o.Unique_Order_ID = %s
                  AND o.Registered_Clients_Email_Address = %s
            """, (unique_order_id, email))
        else:
            cursor.execute("""
                SELECT o.Unique_Order_ID, o.Flight_ID, f.Plane_ID,
                       o.Unidentified_Guest_Email_Address AS Order_Email,
                       o.Order_Status
                FROM Orders o
                JOIN Flight f ON f.Flight_ID = o.Flight_ID
                WHERE o.Unique_Order_ID = %s
                  AND o.Unidentified_Guest_Email_Address = %s
            """, (unique_order_id, email))

        order = cursor.fetchone()
        if not order:
            flash("Order not found or access denied.", "error")
            return redirect(url_for("order_management", tab="future"))

        if str(order.get("Order_Status", "")).upper() in ("CANCELLED", "CANCELLED_BY_AIRLINE"):
            flash("Cannot select seats for a cancelled order.", "error")
            return redirect(url_for("order_management", tab="future"))

        plane_id = order["Plane_ID"]
        flight_id = order["Flight_ID"]
        order_email = order["Order_Email"]

        # how many tickets
        cursor.execute("""
            SELECT Quantity_of_tickets
            FROM Has_an_order
            WHERE Email_Address = %s
              AND Unique_Order_ID = %s
        """, (order_email, unique_order_id))
        qrow = cursor.fetchone()
        needed = int(qrow["Quantity_of_tickets"]) if qrow and qrow.get("Quantity_of_tickets") is not None else 0
        if needed <= 0:
            flash("No tickets found for this order.", "error")
            return redirect(url_for("order_management", tab="future"))

        # seats list
        cursor.execute("""
            SELECT Row_Num, Column_Number, Class
            FROM Seats
            WHERE Plane_ID = %s
            ORDER BY Row_Num, Column_Number
        """, (plane_id,))
        all_seats = cursor.fetchall()

        # occupied for this flight
        cursor.execute("""
            SELECT ss.Row_Num, ss.Column_Number, ss.Unique_Order_ID
            FROM Selected_Seats ss
            JOIN Orders o ON o.Unique_Order_ID = ss.Unique_Order_ID
            WHERE o.Flight_ID = %s
              AND ss.Plane_ID = %s
              AND ss.Is_Occupied = 1
        """, (flight_id, plane_id))
        occ_rows = cursor.fetchall()

        occupied = {f"{r['Row_Num']}{r['Column_Number']}" for r in occ_rows}
        my_selected = {
            f"{r['Row_Num']}{r['Column_Number']}"
            for r in occ_rows
            if str(r["Unique_Order_ID"]) == str(unique_order_id)
        }

        if request.method == "POST":
            selected = request.form.getlist("seat_choice")

            if len(selected) != needed:
                flash(f"Please select exactly {needed} seats.", "error")
                return render_template(
                    "select_seats.html",
                    unique_order_id=unique_order_id,
                    seats=all_seats,
                    occupied=occupied,
                    selected=my_selected,
                    needed=needed
                )

            # ✅ בלי start_transaction
            # clear previous seats for this order
            cursor.execute("""
                UPDATE Selected_Seats
                SET Is_Occupied = 0
                WHERE Unique_Order_ID = %s
                  AND Plane_ID = %s
            """, (unique_order_id, plane_id))

            for seat_id in selected:
                row_num = int(seat_id[:-1])
                col = seat_id[-1]

                # check if taken by another order on same flight
                cursor.execute("""
                    SELECT 1
                    FROM Selected_Seats ss
                    JOIN Orders o ON o.Unique_Order_ID = ss.Unique_Order_ID
                    WHERE o.Flight_ID = %s
                      AND ss.Plane_ID = %s
                      AND ss.Row_Num = %s
                      AND ss.Column_Number = %s
                      AND ss.Is_Occupied = 1
                      AND ss.Unique_Order_ID <> %s
                    LIMIT 1
                """, (flight_id, plane_id, row_num, col, unique_order_id))
                if cursor.fetchone():
                    conn.rollback()
                    flash("One or more seats are no longer available. Please choose again.", "error")
                    return redirect(url_for("select_seats", unique_order_id=unique_order_id))

                # try update
                cursor.execute("""
                    UPDATE Selected_Seats
                    SET Is_Occupied = 1
                    WHERE Plane_ID = %s
                      AND Unique_Order_ID = %s
                      AND Row_Num = %s
                      AND Column_Number = %s
                """, (plane_id, unique_order_id, row_num, col))

                if cursor.rowcount == 0:
                    cursor.execute("""
                        INSERT INTO Selected_Seats
                          (Plane_ID, Unique_Order_ID, Column_Number, Row_Num, Is_Occupied)
                        VALUES
                          (%s, %s, %s, %s, 1)
                    """, (plane_id, unique_order_id, col, row_num))

            conn.commit()
            flash("Seats saved successfully!", "success")

            # ✅ אחרי מושבים -> סיכום הזמנה (לרשום/אורח)
            return redirect(url_for("order_summary", unique_order_id=int(unique_order_id)))

        return render_template(
            "select_seats.html",
            unique_order_id=unique_order_id,
            seats=all_seats,
            occupied=occupied,
            selected=my_selected,
            needed=needed
        )

    except Exception as e:
        try:
            if conn:
                conn.rollback()
        except Exception:
            pass
        flash(f"Database error while loading/saving seats: {e}", "error")
        return redirect(url_for("order_management", tab="future"))

    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass

# =============================
# DB fetch functions (מתוקן לסכמה שלך)
# =============================
def fetch_selected_seats(unique_order_id, plane_id, conn):
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT Row_Num, Column_Number
            FROM Selected_Seats
            WHERE Unique_Order_ID = %s
              AND Plane_ID = %s
              AND Is_Occupied = 1
            ORDER BY Row_Num, Column_Number
        """, (unique_order_id, plane_id))
        rows = cursor.fetchall()
        return [f"{r['Row_Num']}{r['Column_Number']}" for r in rows]
    finally:
        cursor.close()


def fetch_order_quantity(email_address, unique_order_id, conn):
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT Quantity_of_tickets
            FROM Has_an_order
            WHERE Email_Address = %s
              AND Unique_Order_ID = %s
        """, (email_address, unique_order_id))
        row = cursor.fetchone()
        return int(row["Quantity_of_tickets"]) if row and row.get("Quantity_of_tickets") is not None else 0
    finally:
        cursor.close()


def fetch_future_orders_registered(email_address):
    conn = None
    cursor = None
    results = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT o.Unique_Order_ID,
                   o.Flight_ID,
                   o.Registered_Clients_Email_Address AS Email_Address,
                   o.Flight_Date, o.Order_Status,
                   f.Plane_ID, f.Origin_Airport, f.Destination_Airport,
                   f.Departure_Time, f.Departure_Date
            FROM Orders o
            JOIN Flight f ON f.Flight_ID = o.Flight_ID
            WHERE o.Registered_Clients_Email_Address = %s
              AND CONCAT(f.Departure_Date, ' ', f.Departure_Time) > NOW()
            ORDER BY f.Departure_Date, f.Departure_Time
        """, (email_address,))
        rows = cursor.fetchall()

        for r in rows:
            seats = fetch_selected_seats(r["Unique_Order_ID"], r["Plane_ID"], conn)
            qty = fetch_order_quantity(r["Email_Address"], r["Unique_Order_ID"], conn)

            results.append({
                "unique_order_id": r["Unique_Order_ID"],
                "flight_id": r["Flight_ID"],
                "email_address": r["Email_Address"],
                "flight_date": str(r["Flight_Date"]) if r.get("Flight_Date") else None,
                "order_status": r["Order_Status"],
                "origin_airport": r["Origin_Airport"],
                "destination_airport": r["Destination_Airport"],
                "departure_date": str(r["Departure_Date"]),
                "departure_time": str(r["Departure_Time"]),
                "seats": seats,
                "quantity_of_tickets": qty,
                "cancellable": can_cancel(r["Departure_Date"], r["Departure_Time"]),
            })

        return results

    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass


def fetch_past_orders_registered(email_address):
    conn = None
    cursor = None
    results = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT o.Unique_Order_ID,
                   o.Flight_ID,
                   o.Registered_Clients_Email_Address AS Email_Address,
                   o.Flight_Date, o.Order_Status,
                   f.Plane_ID, f.Origin_Airport, f.Destination_Airport,
                   f.Departure_Time, f.Departure_Date
            FROM Orders o
            JOIN Flight f ON f.Flight_ID = o.Flight_ID
            WHERE o.Registered_Clients_Email_Address = %s
              AND CONCAT(f.Departure_Date, ' ', f.Departure_Time) <= NOW()
            ORDER BY f.Departure_Date DESC, f.Departure_Time DESC
        """, (email_address,))
        rows = cursor.fetchall()

        for r in rows:
            seats = fetch_selected_seats(r["Unique_Order_ID"], r["Plane_ID"], conn)
            qty = fetch_order_quantity(r["Email_Address"], r["Unique_Order_ID"], conn)

            results.append({
                "unique_order_id": r["Unique_Order_ID"],
                "flight_id": r["Flight_ID"],
                "email_address": r["Email_Address"],
                "flight_date": str(r["Flight_Date"]) if r.get("Flight_Date") else None,
                "order_status": r["Order_Status"],
                "origin_airport": r["Origin_Airport"],
                "destination_airport": r["Destination_Airport"],
                "departure_date": str(r["Departure_Date"]),
                "departure_time": str(r["Departure_Time"]),
                "seats": seats,
                "quantity_of_tickets": qty,
                "cancellable": False,
            })

        return results

    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass


def fetch_future_orders_guest(unique_order_id, email_address):
    conn = None
    cursor = None
    results = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT o.Unique_Order_ID,
                   o.Flight_ID,
                   o.Unidentified_Guest_Email_Address AS Email_Address,
                   o.Flight_Date, o.Order_Status,
                   f.Plane_ID, f.Origin_Airport, f.Destination_Airport,
                   f.Departure_Time, f.Departure_Date
            FROM Orders o
            JOIN Flight f ON f.Flight_ID = o.Flight_ID
            WHERE o.Unique_Order_ID = %s
              AND o.Unidentified_Guest_Email_Address = %s
              AND CONCAT(f.Departure_Date, ' ', f.Departure_Time) > NOW()
        """, (unique_order_id, email_address))
        rows = cursor.fetchall()

        for r in rows:
            seats = fetch_selected_seats(r["Unique_Order_ID"], r["Plane_ID"], conn)
            qty = fetch_order_quantity(r["Email_Address"], r["Unique_Order_ID"], conn)

            results.append({
                "unique_order_id": r["Unique_Order_ID"],
                "flight_id": r["Flight_ID"],
                "email_address": r["Email_Address"],
                "flight_date": str(r["Flight_Date"]) if r.get("Flight_Date") else None,
                "order_status": r["Order_Status"],
                "origin_airport": r["Origin_Airport"],
                "destination_airport": r["Destination_Airport"],
                "departure_date": str(r["Departure_Date"]),
                "departure_time": str(r["Departure_Time"]),
                "seats": seats,
                "quantity_of_tickets": qty,
                "cancellable": can_cancel(r["Departure_Date"], r["Departure_Time"]),
            })

        return results

    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass


def fetch_order_details(unique_order_id, user_is_reg: bool, email: str):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if user_is_reg:
            cursor.execute("""
                SELECT o.Unique_Order_ID, o.Flight_ID,
                       o.Registered_Clients_Email_Address AS Email_Address,
                       o.Flight_Date, o.Order_Status,
                       f.Plane_ID,
                       f.Departure_Time, f.Departure_Date,

                       ao.Airport_Name AS origin_airport_name,
                       ao.City AS origin_city,
                       ao.Country AS origin_country,

                       ad.Airport_Name AS dest_airport_name,
                       ad.City AS dest_city,
                       ad.Country AS dest_country

                FROM Orders o
                JOIN Flight f ON f.Flight_ID = o.Flight_ID
                JOIN Airports ao ON ao.Airport_ID = f.Origin_Airport
                JOIN Airports ad ON ad.Airport_ID = f.Destination_Airport
                WHERE o.Unique_Order_ID = %s
                  AND o.Registered_Clients_Email_Address = %s
            """, (unique_order_id, email))
        else:
            cursor.execute("""
                SELECT o.Unique_Order_ID, o.Flight_ID,
                       o.Unidentified_Guest_Email_Address AS Email_Address,
                       o.Flight_Date, o.Order_Status,
                       f.Plane_ID,
                       f.Departure_Time, f.Departure_Date,

                       ao.Airport_Name AS origin_airport_name,
                       ao.City AS origin_city,
                       ao.Country AS origin_country,

                       ad.Airport_Name AS dest_airport_name,
                       ad.City AS dest_city,
                       ad.Country AS dest_country

                FROM Orders o
                JOIN Flight f ON f.Flight_ID = o.Flight_ID
                JOIN Airports ao ON ao.Airport_ID = f.Origin_Airport
                JOIN Airports ad ON ad.Airport_ID = f.Destination_Airport
                WHERE o.Unique_Order_ID = %s
                  AND o.Unidentified_Guest_Email_Address = %s
            """, (unique_order_id, email))

        r = cursor.fetchone()
        if not r:
            return None

        seats = fetch_selected_seats(r["Unique_Order_ID"], r["Plane_ID"], conn)
        qty = fetch_order_quantity(r["Email_Address"], r["Unique_Order_ID"], conn)

        return {
            "unique_order_id": r["Unique_Order_ID"],
            "flight_id": r["Flight_ID"],
            "email_address": r["Email_Address"],
            "flight_date": str(r["Flight_Date"]) if r.get("Flight_Date") else None,
            "order_status": r["Order_Status"],
            "departure_date": str(r["Departure_Date"]),
            "departure_time": str(r["Departure_Time"]),
            "seats": seats,
            "quantity_of_tickets": qty,
            "cancellable": can_cancel(r["Departure_Date"], r["Departure_Time"]),

            "origin_airport_name": r["origin_airport_name"],
            "origin_city": r["origin_city"],
            "origin_country": r["origin_country"],
            "dest_airport_name": r["dest_airport_name"],
            "dest_city": r["dest_city"],
            "dest_country": r["dest_country"],
        }

    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass



# ======================================================
# ===================== ADMIN PART ======================
# ======================================================
# ⚠️ נשאר כמו אצלך (כנראה דורש התאמת סכמות DB כדי לעבוד)

def admin_required():
    return session.get("user_type") == "admin" and session.get("worker_id")

# ... (כל החלק של ADMIN אצלך נשאר כאן כפי שהוא) ...


# -------------------------------------------------------
# Backward compatibility route: אם יש לך לינק ישן ל-admin/login
# -------------------------------------------------------
@app.route('/admin/login')
def admin_login():
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
