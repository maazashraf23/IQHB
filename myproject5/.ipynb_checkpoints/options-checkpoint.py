from flask import Flask, render_template

app = Flask(__name__, template_folder='E:/OneDrive/Desktop/Maaz/IQHB/Task 3/myproject5/')
app.secret_key = 'your_secret_key'

# Define route for options.html
@app.route('/')
def options():
    return render_template('options.html')

# Route for Testleitung login page
@app.route('/testleitung_login')
def testleitung_login():
    return render_template('Login.html')
@app.route('/sc_login')
def sc_login():
    return render_template('sc_login.html')

if __name__ == '__main__':
    app.run(debug=True, port=5002)