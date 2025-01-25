from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_session import Session
from functools import wraps
import os
import secrets
import smtplib
from email.mime.text import MIMEText
from firebase_admin import credentials, initialize_app, auth
import joblib
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# App Configurations
app.secret_key = secrets.token_hex(16)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
Session(app)

# Firebase Initialization
cred = credentials.Certificate("C:/Users/katta/OneDrive/Desktop/Heart-Disease-Prediction-Deployment-master/firebase_keys/heartdisease-7df70-firebase-adminsdk-qffhx-a55f319cb4.json")
initialize_app(cred)

# Load trained heart disease model
heart_disease_model = joblib.load('C:/Users/katta/OneDrive/Desktop/Heart-Disease-Prediction-Deployment-master/random_forest_model.joblib')

# Configure the API key for Google Generative AI
genai.configure(api_key="//Gemini_api")

# Define the model for Google Generative AI
model = genai.GenerativeModel("gemini-1.5-flash")

# Utility Functions
def is_valid_password(password):
    """Validate password strength."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number."
    if not any(c in "@$!%*?&" for c in password):
        return False, "Password must contain at least one special character."
    return True, ""

import os

import requests

def send_password_reset_email(email):
    api_key = 'a55f319cb4a1c1ac9005b879aed2a1b101ded5f7'
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={api_key}"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "requestType": "PASSWORD_RESET",
        "email": email
    }
    response = requests.post(url, headers=headers, json=data)
    response_data = response.json()
    if response.status_code == 200:
        return True, "Password reset email sent successfully! Please check your inbox."
    else:
        return False, response_data.get("error", {}).get("message", "An error occurred.")

def login_required(f):
    """Login required decorator."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('signin'))
        return f(*args, **kwargs)
    return decorated_function

def get_diet_plan(prediction):
    """Generate a diet and exercise plan based on the prediction result."""
    if prediction == 1:
        return {
            'title': 'Diet Plan for Heart Disease Risk',
            'details': [
                'Eat more fruits and vegetables.',
                'Limit salt and sodium intake.',
                'Avoid processed foods and sugars.',
                'Increase omega-3 fatty acids (e.g., salmon).',
                'Exercise regularly and maintain a healthy weight.',
            ],
            'exercise_details': [
                'Start with low-impact exercises like walking or swimming.',
                'Try 30 minutes of moderate exercise 3-5 times a week.',
                'Incorporate strength training exercises 2-3 times a week.',
                'Consult a doctor before starting any intense physical activities.',
            ]
        }
    else:
        return {
            'title': 'Diet Plan for a Healthy Heart',
            'details': [
                'Continue eating a balanced diet.',
                'Maintain a low-fat diet.',
                'Limit red meat intake.',
                'Exercise to maintain cardiovascular health.',
            ],
            'exercise_details': [
                'Continue regular exercise with aerobic activities like running or cycling.',
                'Include strength training exercises for muscle health.',
                'Maintain a routine of at least 30 minutes of exercise most days.',
            ]
        }

@app.route('/')
def index():
    return render_template('main.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        is_valid, message = is_valid_password(password)
        if not is_valid:
            flash(message, 'danger')
            return redirect(url_for('signup'))

        try:
            auth.create_user(email=email, password=password)
            flash('Signup successful! Please sign in.', 'success')
            return redirect(url_for('signin'))
        except Exception as e:
            flash(f'Signup failed: {str(e)}', 'danger')

    return render_template('signup.html')

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            # Firebase authentication
            user = auth.get_user_by_email(email)
            session['user'] = email
            flash('Login successful!', 'success')
            return redirect(url_for('predict'))
        except auth.UserNotFoundError:
            flash('No user found with this email.', 'danger')
        except Exception as e:
            flash(f'Login failed: {str(e)}', 'danger')

    return render_template('signin.html')

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        try:
            # Use Firebase to send the reset password email
            auth.send_password_reset_email(email)
            return jsonify({'success': True, 'message': 'Password reset email sent successfully! Please check your inbox.'})
        except auth.UserNotFoundError:
            return jsonify({'success': False, 'message': 'No user found with this email.'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'Error: {str(e)}'})

    return render_template('reset_password.html')

@app.route('/predict', methods=['GET', 'POST'])
@login_required
def predict():
    if request.method == 'POST':
        try:
            data = [
                int(request.form['age']),
                int(request.form['sex']),
                int(request.form['cp']),
                int(request.form['trestbps']),
                int(request.form['chol']),
                int(request.form['fbs']),
                int(request.form['restecg']),
                int(request.form['thalach']),
                int(request.form['exang']),
                float(request.form['oldpeak']),
                int(request.form['slope']),
                int(request.form['ca']),
                int(request.form['thal'])
            ]
            prediction = heart_disease_model.predict([data])[0]
            # Pass both the prediction and input data to the result page
            return redirect(url_for('result', prediction=prediction, data=data))
        except Exception as e:
            flash(f'Prediction failed: {str(e)}', 'danger')
            return redirect(url_for('predict'))

    return render_template('predict.html')

@app.route('/result')
@login_required
def result():
    prediction = request.args.get('prediction', type=int)
    data = request.args.getlist('data', type=int)  # Assuming data is passed as a list of integers
    diet_plan = get_diet_plan(prediction)
    return render_template('result.html', prediction=prediction, diet_plan=diet_plan, data=data)

@app.route('/chat', methods=['GET'])
def chat_page():
    return render_template('chat_widget.html')

@app.route('/chat', methods=['POST'])
def chat():
    input_text = request.form.get('input', '')

    if not input_text:
        return jsonify({"error": "No input provided."})

    try:
        # Generate the response based on input text
        response = model.generate_content(input_text)
        
        # Return the generated response
        return jsonify({"response": response.text})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
