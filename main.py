from flask import Flask, jsonify
import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv


dotenv_path = os.path.join(os.path.dirname(__file__), 'cred.env')

load_dotenv(dotenv_path)  # This loads the environment variables from the .env file.

app = Flask(__name__)  # Define 'app' here, before using it in decorators.

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

@app.route('/test_connection')
def test_connection():
    conn = get_db_connection()
    if conn is not None:
        return "Connected successfully!"
    else:
        return "Failed to connect."

if __name__ == '__main__':
    app.run(debug=True)