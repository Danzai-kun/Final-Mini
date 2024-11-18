from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from models import db, UserSignUp, Program, Student, Qualification, News, Counsellor, CounsellorsReg 
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from base64 import b64encode
from sqlalchemy.exc import IntegrityError
import logging
from logging.handlers import RotatingFileHandler
import os

# Create the Flask app first
app = Flask(__name__)

# Then set up logging
if not os.path.exists('logs'):
    os.mkdir('logs')
    
file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('Application startup')

# Add near the top of the file, after app creation
app.secret_key = 'your-secret-key-here'  # Replace with a secure secret key

# Define the filter function
@app.template_filter('b64encode')
def b64encode_filter(data):
    try:
        if data is None:
            return None
        if isinstance(data, str):
            data = data.encode('utf-8')
        return b64encode(data).decode('utf-8')
    except Exception as e:
        app.logger.error(f"Error encoding image: {str(e)}")
        return None

# Rest of your configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:#http_Khraw@localhost:5432/CourseApplication'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

@app.route('/Home')
@app.route('/')
def home():
    return render_template('Home.html')

@app.route('/login', methods=['POST'])
def login():
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form
        
    email = data.get('loginEmail') 
    password = data.get('loginPassword')
    
    user = UserSignUp.query.filter_by(Client_Email=email, Client_Password=password).first()
    
    if user:
        # Check if user has a counsellor registration
        registration = CounsellorsReg.query.filter_by(Reg_Email=email).first()
        if registration:
            session['registration_id'] = registration.id
            session['user_email'] = email
        
        return jsonify({'success': True, 'message': 'Login successful', 'redirect': '/dashboard'})
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/signup', methods=['POST']) 
def signup():
    print("Received signup request:", request.get_json())  # Debug print
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form
        
    name = data.get('signupName')
    email = data.get('signupEmail')
    password = data.get('signupPassword')

    try:
        # Check if user already exists
        existing_user = UserSignUp.query.filter_by(Client_Email=email).first()
        if existing_user:
            return jsonify({'success': False, 'message': 'Email already registered'}), 400
            
        new_user = UserSignUp(
            Client_Name=name,
            Client_Email=email, 
            Client_Password=password
        )
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Signup successful', 'redirect': '/dashboard'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/dashboard')
def dashboard():
    return render_template('UserDashboard.html')

@app.route('/logout')
def logout():
    # Add any logout logic here (e.g., clearing session)
    return redirect(url_for('home'))

@app.route('/browse_courses')
def browse_courses():
    # Query all programs from the database
    programs = Program.query.all()
    return render_template('BrowseCourses.html', programs=programs)

@app.route('/program_details/<int:program_id>')
def program_details(program_id):
    program = Program.query.get_or_404(program_id)
    return render_template('BrowseCourses.html', program=program)

@app.route('/studentassessment', methods=['GET'])
def student_assessment():
    # Get all programs for the dropdown
    programs = Program.query.all()
    return render_template('studentassessment.html', programs=programs)

@app.route('/submit_assessment', methods=['POST'])
def submit_assessment():
    try:
        # First, create the Student record
        student = Student(
            Student_Email=request.form['student_email'],
            Student_Fname=request.form['first_name'],
            Student_Lname=request.form['last_name'],
            Student_DOB=datetime.strptime(request.form['dob'], '%Y-%m-%d'),
            Student_Phone=request.form['phone']
        )
        db.session.add(student)

        # Create the Qualification record
        qualification = Qualification(
            student_email=request.form['student_email'],
            program_id=int(request.form['program']),
            class10_percentage=float(request.form['class10_percentage']),
            class12_percentage=float(request.form['class12_percentage']),
            class12_stream=request.form['class12_stream'],
            class10_Yearpass=datetime.strptime(request.form['class10_year'], '%Y-%m-%d'),
            class12_Yearpass=datetime.strptime(request.form['class12_year'], '%Y-%m-%d'),
            class12_Board=request.form['class12_board']
        )
        db.session.add(qualification)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Assessment submitted successfully'})
    except Exception as e:
        db.session.rollback()
        print(str(e))  # For debugging
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/updates')
def updates():
    # Query all news items ordered by date (newest first)
    news_items = News.query.order_by(News.date_posted.desc()).all()
    return render_template('Updates.html', news_items=news_items)

@app.route('/expert_talk')
def expert_talk():
    try:
        counsellors = Counsellor.query.with_entities(
            Counsellor.Counsellor_id,
            Counsellor.counsellor_name,
            Counsellor.counsellor_email,
            Counsellor.counsellor_Pno,
            Counsellor.counsellor_description,
            Counsellor.profile_picture
        ).all()
        
        # Debug print
        print(f"Found {len(counsellors)} counsellors")
        for c in counsellors:
            print(f"Counsellor: {c.counsellor_name}")
            if c.profile_picture:
                print(f"Profile picture type: {type(c.profile_picture)}")
        
        return render_template('ExpertTalk.html', counsellors=counsellors)
    except Exception as e:
        app.logger.error(f"Error in expert_talk route: {str(e)}")
        return render_template('ExpertTalk.html', 
                             counsellors=[], 
                             error_message="Unable to load counsellors. Please try again later.")

@app.route('/counsellor_registration/<int:counsellor_id>')
def counsellor_registration(counsellor_id):
    try:
        # Get the counsellor details
        counsellor = Counsellor.query.get_or_404(counsellor_id)
        
        # Debug print to verify counsellor data
        print(f"Found counsellor: {counsellor.counsellor_name}")
        
        # Render the template with the counsellor data
        return render_template('CounsellorRegistration.html', counsellor=counsellor)
    
    except Exception as e:
        print(f"Error in counsellor_registration route: {str(e)}")  # Debug print
        # Instead of returning JSON, redirect to an error page or show an error message
        return render_template('ExpertTalk.html', 
                             error_message="Unable to access registration page. Please try again.")

@app.route('/submit_counsellor_registration', methods=['POST'])
def submit_counsellor_registration():
    try:
        data = request.get_json()
        
        # Check if registration already exists for this email
        existing_registration = CounsellorsReg.query.filter_by(
            Reg_Email=data['reg_email'],
            Counsellor_id=data['counsellor_id']
        ).first()
        
        if existing_registration:
            return jsonify({
                'success': False,
                'message': 'You have already registered with this counsellor.'
            }), 409  # 409 Conflict status code
        
        new_registration = CounsellorsReg(
            Counsellor_id=data['counsellor_id'],
            Reg_Name=data['reg_name'],
            Reg_Email=data['reg_email'],
            Reg_PNo=data['reg_pno'],
            Reg_Date=datetime.strptime(data['reg_date'], '%Y-%m-%d'),
            Reg_Fee=data['reg_fee'],
            Reg_Payment=data['reg_payment']
        )
        
        db.session.add(new_registration)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Registration completed successfully!',
            'registration_id': new_registration.Reg_ID
        })

    except IntegrityError as e:
        db.session.rollback()
        error_info = str(e.orig)
        
        if 'duplicate key' in error_info.lower():
            if 'reg_email' in error_info.lower():
                message = 'This email is already registered with a counsellor.'
            elif 'reg_pno' in error_info.lower():
                message = 'This phone number is already registered.'
            else:
                message = 'A registration with these details already exists.'
        else:
            message = 'Database constraint violation. Please check your input.'
            
        return jsonify({
            'success': False,
            'message': message
        }), 409

    except ValueError as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Invalid data format. Please check your input.'
        }), 400
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in registration: {str(e)}")  # For debugging
        return jsonify({
            'success': False,
            'message': 'An unexpected error occurred. Please try again.'
        }), 500

@app.route('/counsellor_registrations/<int:counsellor_id>')
def counsellor_registrations(counsellor_id):
    counsellor = Counsellor.query.get_or_404(counsellor_id)
    registrations = CounsellorsReg.query.filter_by(Counsellor_id=counsellor_id).all()
    return render_template('CounsellorRegistrations.html', 
                         counsellor=counsellor, 
                         registrations=registrations)

@app.route('/applicant_form/<int:registration_id>')
def applicant_form(registration_id):
    try:
        # Get the registration details
        registration = CounsellorsReg.query.get_or_404(registration_id)
        
        # Get the counsellor details through the relationship
        counsellor = registration.counsellor
        
        # Create applicant dict from registration data
        applicant = {
            'name': registration.Reg_Name,
            'email': registration.Reg_Email,
            'phone': registration.Reg_PNo,
            'registration_date': registration.Reg_Date,
            'status': f"Fee: {registration.Reg_Fee}, Payment: {registration.Reg_Payment}"
        }
        
        return render_template('applicant_form.html', 
                             counsellor=counsellor,
                             applicant=applicant)
                             
    except Exception as e:
        print(f"Error in applicant_form route: {str(e)}")
        return render_template('error.html', 
                             error_message="Unable to load applicant details. Please try again later.")

@app.route('/privacypolicy')
def privacypolicy():
    return render_template('privacypolicy.html')

@app.route('/api/counsellors')
def get_counsellors():
    try:
        counsellors = Counsellor.query.all()
        return jsonify({
            'success': True,
            'count': len(counsellors),
            'counsellors': [c.to_dict() for c in counsellors]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/debug/counsellors')
def debug_counsellors():
    try:
        counsellors = Counsellor.query.all()
        debug_info = {
            'count': len(counsellors),
            'counsellors': [{
                'id': c.Counsellor_id,
                'name': c.counsellor_name,
                'email': c.counsellor_email,
                'has_profile_picture': bool(c.profile_picture)
            } for c in counsellors]
        }
        return jsonify(debug_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/about_us')
def about_us():
    return render_template('about_us.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

