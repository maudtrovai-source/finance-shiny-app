from shiny import App, render, ui, reactive
import pandas as pd
import sqlite3
import hashlib
import datetime
import os
from shinywidgets import output_widget, render_widget
import plotly.graph_objects as go

# --- 1. SETUP DATABASE ---
# We delete the old one if it exists to prevent "Locked" errors during testing
db_file = "finance.db"

def init_db():
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  username TEXT, date TEXT, type TEXT, 
                  category TEXT, description TEXT, amount REAL)''')
    conn.commit()
    conn.close()

# Run initialization
init_db()

# --- 2. SECURITY & DATA FUNCTIONS ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_user(username, password):
    try:
        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE username = ?", (username,))
        row = c.fetchone()
        conn.close()
        return row and row[0] == hash_password(password)
    except:
        return False

def create_user(username, password):
    try:
        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        c.execute("INSERT INTO users VALUES (?, ?)", (username, hash_password(password)))
        conn.commit()
        conn.close()
        return True
    except:
        return False

# --- 3. UI LAYOUT ---
app_ui = ui.page_fluid(
    ui.output_ui("main_content")
)

# --- 4. SERVER LOGIC ---
def server(input, output, session):
    
    # State: Who is logged in? (None = nobody)
    user_session = reactive.Value(None)
    
    # --- A. SCREEN SWITCHER ---
    @render.ui
    def main_content():
        user = user_session.get()
        if user is None:
            return login_ui()
        else:
            return dashboard_ui(user)

    # --- B. LOGIN SCREEN UI ---
    def login_ui():
        return ui.page_fixed(
            ui.card(
                ui.card_header("🔐 Financial Login"),
                ui.input_text("user_login", "Username"),
                ui.input_password("pass_login", "Password"),
                ui.input_action_button("btn_login", "Log In", class_="btn-primary"),
                ui.hr(),
                ui.h5("Create Account"),
                ui.input_text("user_signup", "New Username"),
                ui.input_password("pass_signup", "New Password"),
                ui.input_action_button("btn_signup", "Sign Up", class_="btn-success"),
                style="max-width: 400px; margin-top: 50px; margin-left: auto; margin-right: auto;"
            )
        )

    # --- C. LOGIN LOGIC ---
    @reactive.Effect
    @reactive.event(input.btn_login)
    def _login():
        if verify_user(input.user_login(), input.pass_login()):
            user_session.set(input.user_login())
            ui.notification_show("Login Successful!", type="message")
        else:
            ui.notification_show("Invalid credentials.", type="error")

    @reactive.Effect
    @reactive.event(input.btn_signup)
    def _signup():
        if not input.user_signup() or not input.pass_signup():
            ui.notification_show("Fields cannot be empty", type="warning")
            return
        if create_user(input.user_signup(), input.pass_signup()):
            user_session.set(input.user_signup()) # Auto-login
            ui.notification_show("Account Created!", type="message")
        else:
            ui.notification_show("Username taken.", type="error")

    # --- D. DASHBOARD UI ---
    def dashboard_ui(user):
        return ui.page_sidebar(
            ui.sidebar(
                ui.h4(f"User: {user}"),
                ui.input_radio_buttons("txn_type", "Type", ["Expense (-)", "Income (+)"]),
                ui.input_date("txn_date", "Date", value=datetime.date.today()),
                ui.input_text("txn_desc", "Description", placeholder="e.g. Coffee"),
                ui.input_numeric("txn_amt", "Amount", value=0.0),
                ui.input_select("txn_cat", "Category", ["Food", "Rent", "Salary", "Other"]),
                ui.input_action_button("btn_save", "Save", class_="btn-primary"),
                ui.hr(),
                ui.input_action_button("btn_logout", "Log Out")
            ),
            ui.layout_columns(
                ui.value_box("Net Balance", ui.output_text("val_bal")),
                ui.value_box("Income", ui.output_text("val_inc")),
                ui.value_box("Expenses", ui.output_text("val_exp")),
            ),
            ui.card(output_widget("main_plot")),
            ui.card(ui.output_data_frame("main_table"))
        )

    # --- E. DASHBOARD LOGIC ---
    @reactive.calc
    def get_data():
        # Refresh when save button is clicked
        input.btn_save() 
        user = user_session.get()
        if not user: return pd.DataFrame()
        
        try:
            conn = sqlite3.connect(db_file)
            df = pd.read_sql("SELECT * FROM transactions WHERE username = ?", conn, params=(user,))
            conn.close()
            return df
        except:
            return pd.DataFrame()

    @reactive.Effect
    @reactive.event(input.btn_save)
    def _save():
        user = user_session.get()
        if not user or input.txn_amt() == 0: return
        
        amt = abs(input.txn_amt())
        if input.txn_type() == "Expense (-)": amt = -amt
        
        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        c.execute("INSERT INTO transactions (username, date, type, category, description, amount) VALUES (?, ?, ?, ?, ?, ?)",
                  (user, str(input.txn_date()), input.txn_type(), input.txn_cat(), input.txn_desc(), amt))
        conn.commit()
        conn.close()
        
        ui.update_numeric("txn_amt", value=0.0)
        ui.notification_show("Saved!")

    @reactive.Effect
    @reactive.event(input.btn_logout)
    def _logout():
        user_session.set(None)

    # --- F. OUTPUTS ---
    @render.text
    def val_bal():
        df = get_data()
        return f"${df['amount'].sum():,.2f}" if not df.empty else "$0.00"

    @render.text
    def val_inc():
        df = get_data()
        return f"${df[df['amount']>0]['amount'].sum():,.2f}" if not df.empty else "$0.00"

    @render.text
    def val_exp():
        df = get_data()
        return f"${abs(df[df['amount']<0]['amount'].sum()):,.2f}" if not df.empty else "$0.00"

    @render.data_frame
    def main_table():
        return render.DataGrid(get_data())

    @render_widget
    def main_plot():
        df = get_data()
        if df.empty: return go.Figure()
        
        inc = df[df["amount"] > 0]["amount"].sum()
        exp = df[df["amount"] < 0]["amount"].sum()
        
        return go.Figure(go.Waterfall(
            x = ["Income", "Expenses", "Net"],
            y = [inc, exp, inc+exp],
            measure = ["relative", "relative", "total"]
        ))
app = App(app_ui, server)