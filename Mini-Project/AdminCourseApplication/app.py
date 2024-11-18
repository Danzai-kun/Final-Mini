from flask import Flask, render_template, request, jsonify, session, redirect, url_for, make_response, flash
from models import db, Admin, Staff, News, University, Counsellor, CounsellorsReg, Program, CourseLibrary
from flask_sqlalchemy import SQLAlchemy
import logging
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from werkzeug.utils import secure_filename
import os
import base64
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect

# Define maximum file size (3MB in bytes)
MAX_FILE_SIZE = 3 * 1024 * 1024

# Set up logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

# PostgreSQL database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:#http_Khraw@localhost:5432/CourseApplication'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Add this after db.init_app(app)
with app.app_context():
    # Drop all tables
    # Create all tables
    db.create_all()

app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key

# Combine error handling and authentication into one decorator
def protected_route(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Authentication check
        if 'admin_id' not in session and 'staff_id' not in session and 'counsellor_id' not in session:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Session expired'}), 401
            return redirect(url_for('home'))
        
        # Error handling
        try:
            return f(*args, **kwargs)
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"Database error: {str(e)}")
            return jsonify({'success': False, 'message': 'Database error'}), 500
        except Exception as e:
            logging.error(f"Error: {str(e)}")
            return jsonify({'success': False, 'message': 'Server error'}), 500
    return decorated_function

@app.route('/')
def home():
    return render_template('Homepage.html')

@app.route('/privacypolicy')
def privacypolicy():
    return render_template('privacypolicy.html')

@app.route('/staff/university', methods=['POST'])
@protected_route
def add_university():
    try:
        data = request.get_json()
        
        # Convert deadline string to date object
        deadline = datetime.strptime(data['deadline'], '%Y-%m-%d').date() if data.get('deadline') else None
        
        new_university = University(
            name=data['name'],
            description=data['description'],
            ranking=int(data['ranking']),
            admission_requirements=data['requirements'],
            admission_deadline=deadline,
            career_prospects=data['prospects']
        )
        
        db.session.add(new_university)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'University added successfully',
            'university': {
                'id': new_university.id,
                'name': new_university.name
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error adding university: {str(e)}'
        }), 500

@app.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    username = data['username']
    password = data['password']
    
    admin = Admin.query.filter_by(username=username).first()
    
    if admin and admin.password == password:
        session['admin_id'] = admin.id
        session['admin_username'] = admin.username
        return jsonify({'success': True, 'redirect': '/admin/dashboard'})
    
    return jsonify({'success': False, 'message': 'Invalid credentials'})

@app.route('/admin/dashboard')
@protected_route
def admin_dashboard():
    return render_template('admin_dashboard.html')

# Simplified logout routes into one
@app.route('/logout')
def logout():
    # Clear all session data
    session.clear()
    # Redirect to home page
    return redirect(url_for('home'))

@app.route('/staff/login', methods=['POST'])
def staff_login():
    try:
        data = request.get_json()
        email = data.get('email')
        position = data.get('position')
        password = data.get('password')

        # Add debug logging
        print(f"Login attempt - Email: {email}, Position: {position}")

        if not email or not position or not password:
            return jsonify({
                'success': False,
                'message': 'Email, position and password are required'
            }), 400

        # Query the staff from database
        staff = Staff.query.filter_by(email=email, position=position).first()
        
        # Add debug logging
        if staff:
            print(f"Staff found - DB Password: {staff.password}, Provided Password: {password}")
        else:
            print("No staff found with provided email and position")

        if staff and staff.password == password:  # In production, use proper password hashing
            session['staff_id'] = staff.id
            session['staff_email'] = staff.email
            session['staff_position'] = staff.position
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'redirect': '/staff/dashboard'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Invalid credentials'
            }), 401

    except Exception as e:
        print(f"Login error: {str(e)}")  # Add error logging
        return jsonify({
            'success': False,
            'message': f'Login failed: {str(e)}'
        }), 500

@app.route('/staff/dashboard')
@protected_route  # You'll need to modify this decorator to check for staff session
def staff_dashboard():
    return render_template('staff_dashboard.html')

@app.route('/create-staff', methods=['GET'])
def create_staff():
    try:
        # Check if test staff already exists
        existing_staff = Staff.query.filter_by(email='staff@test.com').first()
        if existing_staff is None:
            staff = Staff(
                email='staff@test.com',
                password='staff123',  # In production, use password hashing
                position='Program Coordinator'
            )
            db.session.add(staff)
            db.session.commit()
            return jsonify({
                'success': True,
                'message': 'Staff account created successfully',
                'staff': {
                    'email': staff.email,
                    'position': staff.position
                }
            })
        return jsonify({
            'success': False,
            'message': 'Staff account already exists',
            'staff': {
                'email': existing_staff.email,
                'position': existing_staff.position
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error creating staff account: {str(e)}'
        })

# Simplified image validation
def validate_profile_picture(image_data):
    if ';base64,' in image_data:
        image_data = image_data.split(';base64,')[1]
    
    decoded_image = base64.b64decode(image_data)
    if len(decoded_image) > MAX_FILE_SIZE:
        return False, 'Image too large'
    
    return True, image_data

@app.route('/admin/add-staff', methods=['POST'])
@protected_route
def add_staff():
    try:
        if not request.is_json:
            return jsonify({
                'success': False,
                'message': 'Content-Type must be application/json'
            }), 415

        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'email', 'position', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'{field} is required'
                }), 400

        # Validate and process profile picture if provided
        profile_picture = None
        if data.get('profile_picture'):
            is_valid, result = validate_profile_picture(data['profile_picture'])
            if not is_valid:
                return jsonify({
                    'success': False,
                    'message': result
                }), 400
            profile_picture = result

        # Create new staff member
        new_staff = Staff(
            name=data['name'],
            email=data['email'],
            position=data['position'],
            password=data['password'],
            profile_picture=profile_picture
        )
        
        db.session.add(new_staff)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Staff member added successfully'
        })

    except IntegrityError as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Email already exists'
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'An error occurred while adding staff member: {str(e)}'
        }), 500

@app.route('/staff/universities', methods=['GET'])
@protected_route
def get_universities():
    try:
        # Fetch all universities with their programs
        universities = University.query.all()
        university_data = []
        
        for uni in universities:
            # Get all programs for this university
            programs = Program.query.filter_by(university_id=uni.id).count()
            
            university_data.append({
                'id': uni.id,
                'name': uni.name,
                'description': uni.description,
                'ranking': uni.ranking,
                'admission_deadline': uni.admission_deadline,
                'program_count': programs
            })
            
        # Check if request wants JSON (from AJAX) or HTML page
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'universities': [{'id': uni['id'], 'name': uni['name']} for uni in university_data]
            })
        
        # Otherwise return the HTML template
        return render_template('universities_details.html', universities=university_data)
        
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500
        flash('Error loading universities: ' + str(e), 'error')
        return redirect(url_for('staff_dashboard'))

@app.route('/staff/program', methods=['POST'])
@protected_route
def add_program():
    try:
        data = request.get_json()
        
        # Create new program
        new_program = Program(
            Program_name=data['name'],
            Program_description=data['description'],
            university_id=int(data['university_id']),
            duration=data['duration'],
            requirements=data['requirements'],
            career_prospects=data['career_prospects']
        )
        
        db.session.add(new_program)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Program added successfully',
            'program': {
                'id': new_program.Program_id,
                'name': new_program.Program_name
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error adding program: {str(e)}'
        }), 500

@app.route('/admin/add-counsellor', methods=['POST'])
@protected_route
def add_counsellor():
    try:
        if not request.is_json:
            return jsonify({
                'success': False,
                'message': 'Content-Type must be application/json'
            }), 415

        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'email', 'phone', 'description', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'{field} is required'
                }), 400

        # Convert profile picture to bytes if provided
        profile_picture = None
        if data.get('profile_picture'):
            try:
                # Remove the data URL prefix if present
                image_data = data['profile_picture']
                if ';base64,' in image_data:
                    image_data = image_data.split(';base64,')[1]
                profile_picture = base64.b64decode(image_data)
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'Error processing profile picture: {str(e)}'
                }), 400

        # Create new counsellor with hashed password
        hashed_password = generate_password_hash(data['password'])
        new_counsellor = Counsellor(
            counsellor_name=data['name'],
            counsellor_email=data['email'],
            counsellor_Pno=data['phone'],
            counsellor_description=data['description'],
            counsellor_password=hashed_password,
            profile_picture=profile_picture
        )
        
        db.session.add(new_counsellor)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Counsellor added successfully',
            'counsellor': {
                'id': new_counsellor.Counsellor_id,
                'name': new_counsellor.counsellor_name,
                'email': new_counsellor.counsellor_email
            }
        })

    except IntegrityError:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'A counsellor with this email already exists'
        }), 409
    except Exception as e:
        db.session.rollback()
        print("Error adding counsellor:", str(e))
        return jsonify({
            'success': False,
            'message': f'Error adding counsellor: {str(e)}'
        }), 500

@app.route('/admin/staff-details')
@protected_route
def staff_details():
    try:
        staff_members = Staff.query.all()
        return render_template('staff_details.html', staff_members=staff_members)
    except Exception as e:
        flash('Error loading staff details: ' + str(e), 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/counsellor-details')
@protected_route
def counsellor_details():
    try:
        counsellors = Counsellor.query.all()
        counsellor_data = [counsellor.to_dict() for counsellor in counsellors]
        return render_template('counsellor_details.html', counsellors=counsellor_data)
    except Exception as e:
        flash('Error loading counsellor details: ' + str(e), 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete-staff/<int:id>', methods=['POST'])
@protected_route
def delete_staff(id):
    try:
        staff = Staff.query.get_or_404(id)
        db.session.delete(staff)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Staff member deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error deleting staff member: {str(e)}'
        }), 500

@app.route('/admin/delete-counsellor/<int:id>', methods=['DELETE'])
@protected_route
def delete_counsellor(id):
    try:
        counsellor = Counsellor.query.get_or_404(id)
        
        # Delete associated registrations first (if any)
        CounsellorsReg.query.filter_by(Counsellor_id=id).delete()
        
        db.session.delete(counsellor)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Counsellor deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error deleting counsellor: {str(e)}'
        }), 500

@app.route('/ExpertTalk')
def expert_talk():
    try:
        # Fetch all counselors from the database
        counsellors = Counsellor.query.all()
        
        # For debugging
        print(f"Found {len(counsellors)} counsellors")
        
        return render_template('ExpertTalk.html', counsellors=counsellors)
    except Exception as e:
        print(f"Error in expert_talk route: {str(e)}")
        return render_template('ExpertTalk.html', counsellors=[])

@app.route('/counsellor_registration/<int:counsellor_id>')
def counsellor_registration(counsellor_id):
    try:
        counsellor = Counsellor.query.get_or_404(counsellor_id)
        return render_template('counsellor_registration.html', counsellor=counsellor)
    except Exception as e:
        flash('Error loading counsellor registration: ' + str(e), 'error')
        return redirect(url_for('expert_talk'))

@app.route('/counsellor/login', methods=['POST'])
def counsellor_login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        print(f"Login attempt - Email: {email}")  # Debug log

        counsellor = Counsellor.query.filter_by(counsellor_email=email).first()
        
        if counsellor and check_password_hash(counsellor.counsellor_password, password):
            # Set session variables
            session.clear()  # Clear any existing session
            session['counsellor_id'] = counsellor.Counsellor_id
            session['user_type'] = 'counsellor'
            
            print(f"Session set: {session}")  # Debug log
            
            return jsonify({
                'success': True,
                'redirect': '/counsellor/dashboard'
            })
        
        return jsonify({
            'success': False,
            'message': 'Invalid email or password'
        }), 401

    except Exception as e:
        print(f"Login error: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/counsellor/dashboard')
@protected_route
def counsellor_dashboard():
    if 'counsellor_id' not in session:
        return redirect(url_for('home'))
    
    try:
        counsellor = Counsellor.query.get_or_404(session['counsellor_id'])
        # Convert counsellor to dictionary to handle profile picture encoding
        counsellor_data = counsellor.to_dict()
        registrations = CounsellorsReg.query.filter_by(Counsellor_id=counsellor.Counsellor_id).all()
        
        print(f"Loading dashboard for counsellor: {counsellor.counsellor_name}")
        print(f"Found {len(registrations)} registrations")
        
        return render_template('counsellor_dashboard.html', 
                             counsellor=counsellor_data,
                             registrations=registrations)
                              
    except Exception as e:
        print(f"Dashboard error: {str(e)}")
        return redirect(url_for('home'))

@app.route('/check-counsellor/<email>')
def check_counsellor(email):
    try:
        counsellor = Counsellor.query.filter_by(counsellor_email=email).first()
        if counsellor:
            return jsonify({
                'found': True,
                'name': counsellor.counsellor_name,
                'password_hash': counsellor.counsellor_password
            })
        return jsonify({
            'found': False,
            'message': 'Counsellor not found'
        })
    except Exception as e:
        return jsonify({
            'error': str(e)
        })

@app.route('/update-counsellor-password/<email>', methods=['POST'])
def update_counsellor_password():
    try:
        data = request.get_json()
        counsellor = Counsellor.query.filter_by(counsellor_email=data['email']).first()
        if counsellor:
            # Hash the password
            hashed_password = generate_password_hash(data['password'])
            counsellor.counsellor_password = hashed_password
            db.session.commit()
            return jsonify({
                'success': True,
                'message': 'Password updated successfully'
            })
        return jsonify({
            'success': False,
            'message': 'Counsellor not found'
        }), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/create-test-counsellor', methods=['GET'])
def create_test_counsellor():
    try:
        # Check if test counsellor already exists
        existing_counsellor = Counsellor.query.filter_by(counsellor_email='test@counsellor.com').first()
        if existing_counsellor is None:
            # Create a test counsellor with a known password
            password = 'test123'
            hashed_password = generate_password_hash(password)
            
            counsellor = Counsellor(
                counsellor_name='Test Counsellor',
                counsellor_email='test@counsellor.com',
                counsellor_Pno='1234567890',
                counsellor_description='Test counsellor account',
                counsellor_password=hashed_password
            )
            
            db.session.add(counsellor)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Test counsellor created successfully',
                'credentials': {
                    'email': 'test@counsellor.com',
                    'password': 'test123'
                }
            })
        return jsonify({
            'success': False,
            'message': 'Test counsellor already exists',
            'credentials': {
                'email': 'test@counsellor.com',
                'password': 'test123'
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error creating test counsellor: {str(e)}'
        })

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/staff/logout')
def staff_logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/counsellor/logout')
def counsellor_logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/debug/counsellors')
def debug_counsellors():
    counsellors = Counsellor.query.all()
    return jsonify({
        'count': len(counsellors),
        'counsellors': [{
            'id': c.Counsellor_id,
            'name': c.counsellor_name,
            'email': c.counsellor_email
        } for c in counsellors]
    })

@app.route('/staff/universities')
@protected_route
def staff_universities():
    try:
        # Fetch all universities with their programs
        universities = University.query.all()
        university_data = []
        
        for uni in universities:
            # Get all programs for this university
            programs = Program.query.filter_by(university_id=uni.id).count()
            
            university_data.append({
                'id': uni.id,
                'name': uni.name,
                'description': uni.description,
                'ranking': uni.ranking,
                'admission_deadline': uni.admission_deadline,
                'program_count': programs
            })
            
        return render_template('universities_details.html', universities=university_data)
    except Exception as e:
        flash('Error loading universities: ' + str(e), 'error')
        return redirect(url_for('staff_dashboard'))

@app.route('/universities')
def universities():
    try:
        # Fetch all universities with their programs
        universities = University.query.all()
        university_data = []
        
        for uni in universities:
            # Get all programs for this university
            programs = Program.query.filter_by(university_id=uni.id).count()
            
            university_data.append({
                'id': uni.id,
                'name': uni.name,
                'description': uni.description,
                'ranking': uni.ranking,
                'admission_deadline': uni.admission_deadline,
                'program_count': programs
            })
            
        return render_template('universities_details.html', universities=university_data)
    except Exception as e:
        flash('Error loading universities: ' + str(e), 'error')
        return redirect(url_for('home'))

@app.route('/university/<int:university_id>')
def university_detail(university_id):
    try:
        university = University.query.get_or_404(university_id)
        programs = Program.query.filter_by(university_id=university_id).all()
        return render_template('university_detail.html', university=university, programs=programs)
    except Exception as e:
        flash('Error loading university details: ' + str(e), 'error')
        return redirect(url_for('universities'))

@app.route('/staff/news-list')
@protected_route
def news_list():
    try:
        # Fetch all news articles ordered by date (most recent first)
        news_articles = News.query.order_by(News.date_posted.desc()).all()
        return render_template('news_details.html', news_list=news_articles)
    except Exception as e:
        flash('Error loading news: ' + str(e), 'error')
        return redirect(url_for('staff_dashboard'))

@app.route('/news/<int:news_id>')
def news_details(news_id):
    try:
        news = News.query.get_or_404(news_id)
        return render_template('news_article.html', news=news)
    except Exception as e:
        flash('Error loading news article: ' + str(e), 'error')
        return redirect(url_for('news_list'))

@app.route('/staff/news', methods=['POST'])
@protected_route
def add_news():
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('title') or not data.get('content'):
            return jsonify({
                'success': False,
                'message': 'Title and content are required'
            }), 400

        # Create new news article
        new_news = News(
            title=data['title'],
            content=data['content'],
            staff_id=session['staff_id']  # Get staff_id from session
        )
        
        db.session.add(new_news)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'News posted successfully',
            'news': {
                'id': new_news.id,
                'title': new_news.title,
                'date_posted': new_news.date_posted.isoformat()
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error posting news: {str(e)}'
        }), 500

@app.route('/staff/delete-news/<int:news_id>', methods=['POST'])
@protected_route
def delete_news(news_id):
    try:
        news = News.query.get_or_404(news_id)
        db.session.delete(news)
        db.session.commit()
        flash('News deleted successfully', 'success')
        return redirect(url_for('news_list'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting news: {str(e)}', 'error')
        return redirect(url_for('news_list'))

@app.route('/news')
def news():
    try:
        # Fetch all news articles ordered by date (most recent first)
        news_articles = News.query.order_by(News.date_posted.desc()).all()
        return render_template('news_details.html', news_list=news_articles)
    except Exception as e:
        flash('Error loading news: ' + str(e), 'error')
        return redirect(url_for('home'))

@app.route('/programs')
@protected_route
def programs():
    # Fetch programs from the database
    programs = Program.query.all()
    return render_template('program_details.html', programs=programs)

@app.route('/staff/delete-program/<int:program_id>', methods=['DELETE'])
@protected_route
def delete_program(program_id):
    try:
        logging.debug(f"Attempting to delete program with ID: {program_id}")
        
        program = Program.query.get_or_404(program_id)
        logging.debug(f"Program found: {program.Program_name}")
        
        db.session.delete(program)
        db.session.commit()
        
        logging.info(f"Program with ID {program_id} deleted successfully")
        return jsonify({'success': True, 'message': 'Program deleted successfully'})
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting program: {str(e)}")
        return jsonify({'success': False, 'message': f'Error deleting program: {str(e)}'}), 500

@app.route('/staff/university/<int:university_id>', methods=['DELETE'])
@protected_route
def delete_university(university_id):
    try:
        university = University.query.get_or_404(university_id)
        # Delete associated programs first (if any)
        Program.query.filter_by(university_id=university_id).delete()
        db.session.delete(university)
        db.session.commit()
        return jsonify({'success': True, 'message': 'University deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error deleting university: {str(e)}'}), 500

@app.route('/admin/add-course', methods=['POST'])
@protected_route
def add_course():
    try:
        if not request.is_json:
            return jsonify({
                'success': False,
                'message': 'Content-Type must be application/json'
            }), 415

        data = request.get_json()

        # Validate required fields
        required_fields = ['name', 'description', 'career_prospects']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'{field} is required'
                }), 400

        # Convert course picture to bytes if provided
        course_picture = None
        if data.get('course_picture'):
            try:
                # Remove the data URL prefix if present
                image_data = data['course_picture']
                if ';base64,' in image_data:
                    image_data = image_data.split(';base64,')[1]
                course_picture = base64.b64decode(image_data)
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'Error processing course picture: {str(e)}'
                }), 400

        # Create new course
        new_course = CourseLibrary(
            Course_name=data['name'],
            Course_description=data['description'],
            career_prospects=data['career_prospects'],
            course_picture=course_picture
        )

        db.session.add(new_course)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Course added successfully',
            'course': {
                'id': new_course.Course_id,
                'name': new_course.Course_name
            }
        })

    except IntegrityError:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'A course with this name already exists'
        }), 409
    except Exception as e:
        logging.error(f"Error adding course: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'An error occurred while adding the course: {str(e)}'
        }), 500

@app.route('/course-library-details')
@protected_route
def course_library_details():
    try:
        # Fetch all courses from the database
        courses = CourseLibrary.query.all()
        course_data = [{
            'Course_name': course.Course_name,
            'Course_description': course.Course_description,
            'career_prospects': course.career_prospects,
            'course_picture': base64.b64encode(course.course_picture).decode('utf-8') if course.course_picture else None
        } for course in courses]
        
        # Render the template with course data
        return render_template('courseLibrary_details.html', courses=course_data)
    except Exception as e:
        logging.error(f"Error loading course details: {str(e)}")
        flash('Error loading course details', 'error')
        return redirect(url_for('home'))

@app.route('/api/courses', methods=['GET'])
@protected_route
def get_courses():
    try:
        courses = CourseLibrary.query.all()
        course_data = [{
            'id': course.Course_id,
            'name': course.Course_name,
            'description': course.Course_description,
            'career_prospects': course.career_prospects,
            'course_picture': base64.b64encode(course.course_picture).decode('utf-8') if course.course_picture else None
        } for course in courses]
        
        logging.debug(f"Course data: {course_data[:1]}")  # Log only the first course for brevity
        
        return jsonify({'success': True, 'courses': course_data})
    except Exception as e:
        logging.error(f"Error retrieving courses: {str(e)}")
        return jsonify({'success': False, 'message': 'Error retrieving courses'}), 500

@app.route('/admin/delete-course/<int:course_id>', methods=['DELETE'])
@protected_route
def delete_course(course_id):
    try:
        # Fetch the course from the database
        course = CourseLibrary.query.get_or_404(course_id)
        
        # Delete the course
        db.session.delete(course)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Course deleted successfully'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error deleting course: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)
