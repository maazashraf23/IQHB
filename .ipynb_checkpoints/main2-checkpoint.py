from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import pyodbc
import hashlib
import datetime
import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

app = Flask(__name__, template_folder='E:/OneDrive/Desktop/Maaz/IQHB/Task 3/myproject11/')
app.secret_key = 'your_secret_key'


dotenv_path = os.path.join(os.path.dirname(__file__), 'cred.env')

load_dotenv(dotenv_path)  # This loads the environment variables from the .env file.

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user=os.getenv('MYSQL_USER'),
            password=os.getenv('MYSQL_PASSWORD'),
            database=os.getenv('MYSQL_DB')
        )
        if connection.is_connected():
            db_info = connection.get_server_info()
            print("Successfully connected to MySQL Server version ", db_info)
            return connection
    except Error as e:
        print("Error while connecting to MySQL", e)
        return None

# Create the connection string
#conn_str = f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;'

# Function to hash passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()




#-----------------------------------------------------------------------  Main Page ---------------------------------------------------------

@app.route('/')
def options():
    return render_template('options.html')

# Route for Testleitung login page
@app.route('/testleitung_login')
def testleitung_login():
    return render_template('Login.html')

@app.route('/haupttestleitung_login')
def hauptesttleitung_login():
    return render_template('htl_login.html')

@app.route('/haupttestleitung_signup')
def hauptesttleitung_signup():
    return render_template('htl_signup.html')
    


#-----------------------------------------------------------------------  Testleitung ---------------------------------------------------------


# Function to authenticate user against the database
def authenticate_user_signup(email, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    hashed_password = hash_password(password)
    cursor.execute("SELECT * FROM Sheet1 WHERE UID=%s", (email,))
    user = cursor.fetchone()
    conn.close()
    return user


#login authentication for Testleitung
def authenticate_user_login(email, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    hashed_password = hash_password(password)
    cursor.execute("SELECT * FROM IQHB.dbo.[Sheet1$] WHERE UID=%s AND PWD=%s", (email, hashed_password))
    user = cursor.fetchone()
    conn.close()
    return user



# Function to register a new user
def register_user(email, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    hashed_password = hash_password(password)
    cursor.execute("INSERT INTO IQHB.[Sheet1$] (UID, PWD) VALUES (%s, %s)", (email, hashed_password))
    conn.commit()
    conn.close()

# Function to get shifts, school, and class for a selected date
def get_shifts(selected_date):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Execute the SQL query to get the school name, class, and check if the shift is taken for the selected date
    cursor.execute("SELECT DISTINCT School, Class, ShiftTaken FROM IQHB.[Tabelle1$] WHERE Date = %s", (selected_date,))
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

    conn = get_db_connection()
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
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Update the database to mark the shift as available
        sql = "UPDATE [IQHB].[dbo].[Tabelle1$] SET ShiftTaken = NULL WHERE Date = %s AND School = %s AND Class = %s AND ShiftTaken = %s"
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

    
@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']

    user = authenticate_user_login(email, password)

    if user:
        session['email'] = email
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('testleitung_login'))



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
        conn = get_db_connection()
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
        return redirect(url_for('testleitung_login'))

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
        return redirect(url_for('testleitung_login'))

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
        return redirect(url_for('testleitung_login'))

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('email', None)
    # Redirect to the options page after logout
    return redirect(url_for('options'))



#-----------------------------------------------------------------------  School Cordinator ---------------------------------------------------------

#login authentication for School cordinator


def authenticate_sc_user_login(email, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    hashed_password = hash_password(password)
    print(f"Debug: Email = {email}, Hashed Password = {hashed_password}")
    cursor.execute("SELECT * FROM credentials WHERE Email=%s AND Password=%s", (email, hashed_password))
    user = cursor.fetchone()
    conn.close()
    if user:
        print("Debug: User found.")
    else:
        print("Debug: User not found.")
    return user

#-------------------------------------------------SC_5-------------------------------------------------------------------------
@app.route('/sc_dashboard_5')
def sc_dashboard_5():
    if 'email' in session:
        email = session['email']
        # Check if the email exists in the database
        if email_exists_5(email):
            # Fetch user details only if the email exists
            user_details = fetch_user_details_5(email)
            if user_details:
                # If all required details are present, render the dashboard
                return render_template('sc_dashboard_5.html')
            else:
                # If any detail is missing, redirect to the information update page
                return redirect(url_for('sc_information_page'))
        else:
            # If the email does not exist in the database, potentially log out the user or handle accordingly
            return redirect(url_for('class_page'))
    else:
        # If no user is logged in, redirect to the login page
        return redirect(url_for('sc_login'))




def fetch_user_details_5(email):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Vorname, Nachname, Schule, Addresse, Telephone FROM IQHB.schoolcordinator WHERE Email = %s", (email,))
    user_details = cursor.fetchone()
    cursor.close()
    conn.close()
    if user_details:
        Schule, Addresse, Vorname,Nachname, Telephone = user_details
        if Schule and Addresse and Vorname and Nachname and Telephone:
            return True  # All details are present
    return False  # Details are missing



def email_exists_5(email):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT Email FROM IQHB.schoolcordinator WHERE Email = %s", (email,))
        if cursor.fetchone():
            return True
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

'''def check_sc_user_details(email):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Schule, Addresse, Vorname,Nachname, Telephone FROM schoolcordinator WHERE Email = ?", (email,))
    user_details = cursor.fetchone()
    conn.close()

    if user_details:
        Schule, Addresse, Vorname,Nachname, Telephone = user_details
        if Schule and Addresse and Vorname and Nachname and Telephone:
            return True  # All details are present
    return False  # Details are missing
'''

def check_date_column(email, column):
    conn = get_db_connection()
    cursor = conn.cursor()
    sql = f"SELECT {column} FROM schoolcordinator WHERE Email = %s"
    cursor.execute(sql, (email,))
    row = cursor.fetchone()
    date_value = row[0] if row else None
    cursor.close()
    conn.close()
    return date_value is not None

def update_date(email, date, start_time, column_date, column_start_time):
    conn = get_db_connection()
    cursor = conn.cursor()
    sql = f"UPDATE schoolcordinator SET {column_date} = %s, {column_start_time} = %s WHERE Email = %s"
    cursor.execute(sql, (date, start_time, email))
    conn.commit()
    cursor.close()
    conn.close()

@app.route('/get_chosen_dates')
def get_chosen_dates():
    if 'email' in session:
        email = session['email']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Execute a query to fetch the chosen dates and times for the logged-in user
        cursor.execute("SELECT Date1, StartTime1, Date2, StartTime2, Date3, StartTime3 FROM schoolcordinator WHERE Email=%s", (email,))
        row = cursor.fetchone()  # Assuming only one row is returned
        
        # Extract dates and times from the row and format them as "date at time"
        chosen_dates = []
        for i in range(0, len(row), 2):
            if row[i] is not None and row[i+1] is not None:
                date_time_str = f"{row[i]} at {row[i+1]}"
                chosen_dates.append(date_time_str)
        
        # Close the database connection
        conn.close()
        
        # Return the chosen dates and times as JSON
        return jsonify(chosen_dates=chosen_dates)
    else:
        return jsonify(error='User not logged in')



def check_unique_date(email, date):
    # Query the database to check if the selected date exists in Date1, Date2, or Date3 columns
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM schoolcordinator WHERE Email=%s AND (Date1=%s OR Date2=%s OR Date3=%s)", (email, date, date, date))
    count = cursor.fetchone()[0]
    conn.close()

    # Return True if the count is 0 (i.e., the date is unique), otherwise False
    return count == 0


@app.route('/sc_login')
def sc_login():
    return render_template('sc_login.html')

@app.route('/sc_signup')
def sc_signup():
    return render_template('sc_signup.html')

 
@app.route('/schoolcordinator_login', methods=['POST'])
def schoolcordinator_login():
    email = request.form['email']
    password = request.form['password']
    user = authenticate_sc_user_login(email, password)
    
    if user:
        session['email'] = email
        return redirect(url_for('class_page'))
    else:
        return "Invalid email or password. Please try again."


@app.route('/submit_sc_user_info', methods=['POST'])
def submit_user_info():
    email = session.get('email')
    if email:
        # Get form data
        vorname = request.form['vorname']
        nachname = request.form['nachname']
        schule = request.form['schule']
        adresse = request.form['adresse']
        telephone = request.form['telephone']
        sc_email = request.form['sc_email']
        it_vorname = request.form['it_vorname']
        it_nachname = request.form['it_nachname']
        it_telephone = request.form['it_telephone']
        it_email = request.form['it_email']
        zusatsperson_vorname = request.form['zusatsperson_vorname']
        zusatsperson_nachname = request.form['zusatsperson_nachname']
        zusatsperson_telephone = request.form['zusatsperson_telephone']
        zusatsperson_email = request.form['zusatsperson_email']
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Update user information in the 'schoolcordinator' table
            cursor.execute("""
                UPDATE schoolcordinator 
                SET Vorname = %s, Nachname = %s, Schule = %s, Addresse = %s, Telephone = %s, sc_Email = %s, 
                    IT_Vorname = %s, IT_Nachname = %s, IT_Telephone = %s, IT_Email = %s,
                    Zusatsperson_Vorname = %s, Zusatsperson_Nachname = %s, Zusatsperson_Telephone = %s, Zusatsperson_Email = %s
                WHERE Email = %s""", 
                (vorname, nachname, schule, adresse, telephone, sc_email,
                 it_vorname, it_nachname, it_telephone, it_email,
                 zusatsperson_vorname, zusatsperson_nachname, zusatsperson_telephone, zusatsperson_email,
                 email))

            # Commit the transaction
            conn.commit()

        except Exception as e:
            print("An error occurred:", e)
            # Rollback in case of error
            conn.rollback()
            return jsonify({'success': False, 'message': 'Database operation failed'}), 500

        finally:
            # Ensure the connection is closed
            cursor.close()
            conn.close()

        return redirect(url_for('class_page'))
    else:
        return "User not logged in."


@app.route('/add_date', methods=['POST'])
def add_date():
    if 'email' in session:
        email = session['email']
        date = request.form.get('date')
        start_time = request.form.get('time')  # Get the selected start time from the form

        # Parse the selected time to extract hours and minutes
        hours, minutes = map(int, start_time.split(':'))

        # Check if the selected date is not the same as dates in Date1, Date2, or Date3 columns
        if check_unique_date(email, date):
            # Check if Date1 is empty, if so, populate it
            if not check_date_column(email, 'Date1'):
                update_date(email, date, start_time, 'Date1', 'StartTime1')
            # Check if Date1 is populated but Date2 is empty, if so, populate Date2
            elif not check_date_column(email, 'Date2'):
                update_date(email, date, start_time, 'Date2', 'StartTime2')
            # Check if both Date1 and Date2 are populated but Date3 is empty, if so, populate Date3
            elif not check_date_column(email, 'Date3'):
                update_date(email, date, start_time, 'Date3', 'StartTime3')
            else:
                return jsonify({'success': False, 'message': 'All date columns are already populated.'})
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Selected date already exists in one of the columns.'})
    else:
        return jsonify({'success': False, 'message': 'User not logged in'})



@app.route('/remove_date', methods=['POST'])
def remove_date():
    if 'email' in session:
        email = session['email']
        date_to_remove = request.form.get('date')

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Split the date string to remove the ' at ' and milliseconds
            date_to_remove = date_to_remove.split(' at ')[0]

            # Convert the date string to the appropriate format for SQL Server
            date_to_remove = datetime.datetime.strptime(date_to_remove, '%Y-%m-%d').date()
            
            # Update the database to remove the date and time
            cursor.execute(f"UPDATE schoolcordinator SET Date1 = NULL, StartTime1 = NULL WHERE Email = '{email}' AND Date1 = '{date_to_remove}'")
            cursor.execute(f"UPDATE schoolcordinator SET Date2 = NULL, StartTime2 = NULL WHERE Email = '{email}' AND Date2 = '{date_to_remove}'")
            cursor.execute(f"UPDATE schoolcordinator SET Date3 = NULL, StartTime3 = NULL WHERE Email = '{email}' AND Date3 = '{date_to_remove}'")
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True})
        except Exception as e:
            print("Error removing date:", e)
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': str(e)}), 500
    else:
        return jsonify({'success': False, 'message': 'User not logged in'})





#-------------------------------------------------SC_7-------------------------------------------------------------------------


@app.route('/sc_class_7')
def sc_class_7():
    if 'email' in session:
        email = session['email']
        # Check if the email exists in the database
        if email_exists_7(email):
            # Fetch user details only if the email exists
            user_details = fetch_user_details_7(email)
            if user_details:
                # If all required details are present, render the dashboard
                return render_template('sc_dashboard_7.html')
            else:
                # If any detail is missing, redirect to the information update page
                return redirect(url_for('sc_information_page_7'))
        else:
            # If the email does not exist in the database, potentially log out the user or handle accordingly
            return "Ihre Schule nimmt in diesem Schuljahr (noch) nicht an LALE 7 teil. Bitte klicken Sie auf den LALE 5 Button, um Ihre Wunschtermine anzugeben."
    else:
        # If no user is logged in, redirect to the login page
        return redirect(url_for('sc_login'))




def fetch_user_details_7(email):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Vorname, Nachname, Schule, Addresse, Telephone FROM schoolcordinator_7 WHERE Email = %s", (email,))
    user_details = cursor.fetchone()
    cursor.close()
    conn.close()
    if user_details:
        Schule, Addresse, Vorname,Nachname, Telephone = user_details
        if Schule and Addresse and Vorname and Nachname and Telephone:
            return True  # All details are present
    return False  # Details are missing



def email_exists_7(email):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT Email FROM schoolcordinator_7 WHERE Email = %s", (email,))
        if cursor.fetchone():
            return True
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


@app.route('/submit_sc_user_info_7', methods=['POST'])
def submit_user_info_7():
    email = session.get('email')
    if email:
        # Get form data
        vorname = request.form['vorname']
        nachname = request.form['nachname']
        schule = request.form['schule']
        adresse = request.form['adresse']
        telephone = request.form['telephone']
        sc_email = request.form['sc_email']
        it_vorname = request.form['it_vorname']
        it_nachname = request.form['it_nachname']
        it_telephone = request.form['it_telephone']
        it_email = request.form['it_email']
        zusatsperson_vorname = request.form['zusatsperson_vorname']
        zusatsperson_nachname = request.form['zusatsperson_nachname']
        zusatsperson_telephone = request.form['zusatsperson_telephone']
        zusatsperson_email = request.form['zusatsperson_email']
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Update user information in the 'schoolcordinator' table
            cursor.execute("""
                UPDATE schoolcordinator_7
                SET Vorname = %s, Nachname = %s, Schule = %s, Addresse = %s, Telephone = %s, sc_Email = %s,
                    IT_Vorname = %s, IT_Nachname = %s, IT_Telephone = %s, IT_Email = %s,
                    Zusatsperson_Vorname = %s, Zusatsperson_Nachname = %s, Zusatsperson_Telephone = %s, Zusatsperson_Email = %s
                WHERE Email = %s""", 
                (vorname, nachname, schule, adresse, telephone, sc_email,
                 it_vorname, it_nachname, it_telephone, it_email,
                 zusatsperson_vorname, zusatsperson_nachname, zusatsperson_telephone, zusatsperson_email,
                 email))

            # Commit the transaction
            conn.commit()

        except Exception as e:
            print("An error occurred:", e)
            # Rollback in case of error
            conn.rollback()
            return jsonify({'success': False, 'message': 'Database operation failed'}), 500

        finally:
            # Ensure the connection is closed
            cursor.close()
            conn.close()

        return redirect(url_for('class_page'))
    else:
        return "User not logged in."
        


def check_date_column_7(email, column):
    conn = get_db_connection()
    cursor = conn.cursor()
    sql = f"SELECT {column} FROM schoolcordinator_7 WHERE Email = %s"
    cursor.execute(sql, (email,))
    row = cursor.fetchone()
    date_value = row[0] if row else None
    cursor.close()
    conn.close()
    return date_value is not None

def update_date_7(email, date, start_time, column_date, column_start_time):
    conn = get_db_connection()
    cursor = conn.cursor()
    sql = f"UPDATE schoolcordinator_7 SET {column_date} = %s, {column_start_time} = %s WHERE Email = %s"
    cursor.execute(sql, (date, start_time, email))
    conn.commit()
    cursor.close()
    conn.close()

@app.route('/get_chosen_dates_7')
def get_chosen_dates_7():
    if 'email' in session:
        email = session['email']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Execute a query to fetch the chosen dates and times for the logged-in user
        cursor.execute("SELECT Date1, StartTime1, Date2, StartTime2, Date3, StartTime3 FROM schoolcordinator_7 WHERE Email=%s", (email,))
        row = cursor.fetchone()  # Assuming only one row is returned
        
        # Extract dates and times from the row and format them as "date at time"
        chosen_dates = []
        for i in range(0, len(row), 2):
            if row[i] is not None and row[i+1] is not None:
                date_time_str = f"{row[i]} at {row[i+1]}"
                chosen_dates.append(date_time_str)
        
        # Close the database connection
        conn.close()
        
        # Return the chosen dates and times as JSON
        return jsonify(chosen_dates=chosen_dates)
    else:
        return jsonify(error='User not logged in')



def check_unique_date_7(email, date):
    # Query the database to check if the selected date exists in Date1, Date2, or Date3 columns
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM schoolcordinator_7 WHERE Email=%s AND (Date1=%s OR Date2=%s OR Date3=%s)", (email, date, date, date))
    count = cursor.fetchone()[0]
    conn.close()

    # Return True if the count is 0 (i.e., the date is unique), otherwise False
    return count == 0




@app.route('/add_date_7', methods=['POST'])
def add_date_7():
    if 'email' in session:
        email = session['email']
        date = request.form.get('date')
        start_time = request.form.get('time')  # Get the selected start time from the form

        # Parse the selected time to extract hours and minutes
        hours, minutes = map(int, start_time.split(':'))

        # Check if the selected date is not the same as dates in Date1, Date2, or Date3 columns
        if check_unique_date_7(email, date):
            # Check if Date1 is empty, if so, populate it
            if not check_date_column_7(email, 'Date1'):
                update_date_7(email, date, start_time, 'Date1', 'StartTime1')
            # Check if Date1 is populated but Date2 is empty, if so, populate Date2
            elif not check_date_column_7(email, 'Date2'):
                update_date_7(email, date, start_time, 'Date2', 'StartTime2')
            # Check if both Date1 and Date2 are populated but Date3 is empty, if so, populate Date3
            elif not check_date_column_7(email, 'Date3'):
                update_date_7(email, date, start_time, 'Date3', 'StartTime3')
            else:
                return jsonify({'success': False, 'message': 'All date columns are already populated.'})
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Selected date already exists in one of the columns.'})
    else:
        return jsonify({'success': False, 'message': 'User not logged in'})



@app.route('/remove_date_7', methods=['POST'])
def remove_date_7():
    if 'email' in session:
        email = session['email']
        date_to_remove = request.form.get('date')

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Split the date string to remove the ' at ' and milliseconds
            date_to_remove = date_to_remove.split(' at ')[0]

            # Convert the date string to the appropriate format for SQL Server
            date_to_remove = datetime.datetime.strptime(date_to_remove, '%Y-%m-%d').date()
            
            # Update the database to remove the date and time
            cursor.execute(f"UPDATE schoolcordinator_7 SET Date1 = NULL, StartTime1 = NULL WHERE Email = '{email}' AND Date1 = '{date_to_remove}'")
            cursor.execute(f"UPDATE schoolcordinator_7 SET Date2 = NULL, StartTime2 = NULL WHERE Email = '{email}' AND Date2 = '{date_to_remove}'")
            cursor.execute(f"UPDATE schoolcordinator_7 SET Date3 = NULL, StartTime3 = NULL WHERE Email = '{email}' AND Date3 = '{date_to_remove}'")
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True})
        except Exception as e:
            print("Error removing date:", e)
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': str(e)}), 500
    else:
        return jsonify({'success': False, 'message': 'User not logged in'})




@app.route('/sc_information')
def sc_information_page():
    return render_template('sc_information.html')

@app.route('/sc_information_7')
def sc_information_page_7():
    return render_template('sc_information_7.html')

@app.route('/class')
def class_page():
    if 'email' in session:
        email = session['email']
        return render_template('sc_class.html', email=email)
    else:
        # Redirect to login page or handle the case when email is not in session
        return redirect(url_for('sc_login'))  # Example redirection to the login page







if __name__ == '__main__':
    app.run(debug=True)
