from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import pyodbc
import hashlib
import datetime

app = Flask(__name__, template_folder='E:/OneDrive/Desktop/Maaz/IQHB/Task 3/myproject5/SC/')
app.secret_key = 'your_secret_key'

# Database connection parameters
server = 'localhost\\SQLEXPRESS'
database = 'IQHB'
username = 'your_username'
password = 'your_password'

# Create the connection string
conn_str = f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;'

# Function to hash passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Function to authenticate user against the database
def authenticate_user_signup(email, password):
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    hashed_password = hash_password(password)
    cursor.execute("SELECT * FROM IQHB.dbo.[Sheet1$] WHERE UID=?", (email))
    user = cursor.fetchone()
    conn.close()
    return user

def authenticate_user_login(email, password):
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    hashed_password = hash_password(password)
    cursor.execute("SELECT * FROM IQHB.dbo.[Sheet1$] WHERE UID=? AND PWD=?", (email, hashed_password))
    user = cursor.fetchone()
    conn.close()
    return user

# Function to register a new user
def register_user(email, password):
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    hashed_password = hash_password(password)
    cursor.execute("INSERT INTO IQHB.dbo.[Sheet1$] (UID, PWD) VALUES (?, ?)", (email, hashed_password))
    conn.commit()
    conn.close()

# Function to get shifts, school, and class for a selected date
def get_shifts(selected_date):
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    # Execute the SQL query to get the school name, class, and check if the shift is taken for the selected date
    cursor.execute("SELECT DISTINCT School, Class, ShiftTaken FROM IQHB.dbo.[Tabelle1$] WHERE Date = ?", (selected_date,))
    shifts_info = cursor.fetchall()

    # Filter out shifts that are already taken
    available_shifts = [shift_info for shift_info in shifts_info if not shift_info.ShiftTaken]

    # Close the cursor and connection
    cursor.close()
    conn.close()

    return available_shifts

# Function to take a shift
def take_shift(email, selected_date, school, class_):
    # Parse the selected date string to a Python date object
    selected_date = datetime.datetime.strptime(selected_date, '%Y-%m-%d').date()

    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    # Update the database to mark the shift as taken by the user
    sql = "UPDATE [IQHB].[dbo].[Tabelle1$] SET ShiftTaken = '{}' WHERE Date = '{}' AND School = '{}' AND Class = '{}'".format(email, selected_date, school, class_)
    cursor.execute(sql)
    conn.commit()

    # Close the cursor and connection
    cursor.close()
    conn.close()

# Function to remove a shift
def remove_shift(selected_date, school, class_, email):
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    try:
        # Update the database to mark the shift as available
        sql = "UPDATE [IQHB].[dbo].[Tabelle1$] SET ShiftTaken = NULL WHERE Date = ? AND School = ? AND Class = ? AND ShiftTaken = ?"
        cursor.execute(sql, (selected_date, school, class_, email))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print("Error removing shift:", e)
        cursor.close()
        conn.close()
        return False

@app.route('/')
def index():
    return render_template('sc_login.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']

    user = authenticate_user_login(email, password)

    if user:
        session['email'] = email
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('index'))
@app.route('/signup_page')
def signup_page():
    # Render signup.html for the sign-up page
    return render_template('signup.html')
    
@app.route('/signup', methods=['POST'])
def signup():
    email = request.form['email']
    password = request.form['password']

    # Check if the user already exists
    if authenticate_user_signup(email, password):
        # If email exists, return an error message
        return jsonify({'error': 'Email already in use. Please choose a different email address.'}), 400

    # Register the user since email does not exist
    register_user(email, password)
    session['email'] = email
    return redirect(url_for('dashboard'))


@app.route('/get_email')
def get_email():
    if 'email' in session:
        email = session['email']
        return jsonify({'email': email})
    else:
        return jsonify({'email': None})

@app.route('/dashboard')
def dashboard():
    if 'email' in session:
        email = session['email']
        
        # Fetch shifts taken by the logged-in user
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("SELECT Date, School, Class FROM IQHB.dbo.[Tabelle1$] WHERE ShiftTaken = ?", (email,))
        user_shifts = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return render_template('dashboard.html', email=email, user_shifts=user_shifts)
    else:
        return redirect(url_for('index'))

@app.route('/get_shifts', methods=['POST'])
def get_shifts_route():
    if 'email' in session:
        selected_date = request.json['date']
        
        # Get shifts for the selected date
        shifts_info = get_shifts(selected_date)

        # Convert the Row objects to dictionaries for JSON serialization
        shifts_info_dicts = [{'school': row.School, 'class': row.Class, 'shift_taken': row.ShiftTaken} for row in shifts_info]

        return jsonify({'shifts_info': shifts_info_dicts})
    else:
        return redirect(url_for('index'))

@app.route('/take_shift', methods=['POST'])
def take_shift_route():
    if 'email' in session:
        email = session['email']
        selected_date = request.json['date']
        school = request.json['school']
        class_ = request.json['class']
        
        # Take the shift
        take_shift(email, selected_date, school, class_)

        return jsonify({'success': True})
    else:
        return redirect(url_for('index'))

@app.route('/remove_shift', methods=['POST'])
def remove_shift_route():
    if 'email' in session:
        email = session['email']
        selected_date = request.json['date']
        school = request.json['school']
        class_ = request.json['class']

        # Remove the shift
        success = remove_shift(selected_date, school, class_, email)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False}), 500  # Return an error status code if removal fails
    else:
        return redirect(url_for('index'))

@app.route('/logout', methods=['POST'])  # Ensure that this route accepts POST method
def logout():
    session.pop('email', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5003)
