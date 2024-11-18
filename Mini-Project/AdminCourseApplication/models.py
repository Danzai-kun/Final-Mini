from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.orm import validates
import base64

db = SQLAlchemy()

MAX_FILE_SIZE = 3 * 1024 * 1024  
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/gif'}

def is_allowed_file(file):
    return file.mimetype in ALLOWED_MIME_TYPES


class BaseModel(db.Model):
    __abstract__ = True
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class Admin(BaseModel):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)

class Staff(db.Model):
    __tablename__ = 'staff'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    position = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    profile_picture = db.Column(db.Text, nullable=True)

    def __init__(self, name, email, position, password, profile_picture=None):
        self.name = name
        self.email = email
        self.position = position
        self.password = password
        self.profile_picture = profile_picture

    @validates('email')
    def validate_email(self, key, email):
        if not email or '@' not in email:
            raise ValueError('Invalid email address')
        return email

    @validates('password')
    def validate_password(self, key, password):
        if len(password) < 8:
            raise ValueError('Password must be at least 8 characters')
        return password

class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)

class University(db.Model):
    __tablename__ = 'university'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    ranking = db.Column(db.Integer)
    admission_requirements = db.Column(db.Text)
    admission_deadline = db.Column(db.Date)
    career_prospects = db.Column(db.Text)

class Counsellor(db.Model):
    __tablename__ = 'counsellor'
    Counsellor_id = db.Column(db.Integer, primary_key=True)
    counsellor_name = db.Column(db.String(100), nullable=False)
    counsellor_email = db.Column(db.String(120), unique=True, nullable=False)
    counsellor_Pno = db.Column(db.String(20))
    counsellor_description = db.Column(db.Text)
    counsellor_password = db.Column(db.String(255), nullable=False)
    profile_picture = db.Column(db.LargeBinary)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    registrations = db.relationship('CounsellorsReg', backref='counsellor', lazy=True, cascade='all, delete-orphan')

    def __init__(self, counsellor_name, counsellor_email, counsellor_Pno, counsellor_description, counsellor_password, profile_picture=None):
        self.counsellor_name = counsellor_name
        self.counsellor_email = counsellor_email
        self.counsellor_Pno = counsellor_Pno
        self.counsellor_description = counsellor_description
        self.counsellor_password = counsellor_password
        self.profile_picture = profile_picture

    def to_dict(self):
        data = {
            'id': self.Counsellor_id,
            'name': self.counsellor_name,
            'email': self.counsellor_email,
            'phone': self.counsellor_Pno,
            'description': self.counsellor_description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'registrations': [reg.to_dict() for reg in self.registrations] if self.registrations else []
        }
        
        # Convert binary profile picture to base64 string if it exists
        if self.profile_picture:
            try:
                data['profile_picture'] = f"data:image/jpeg;base64,{base64.b64encode(self.profile_picture).decode('utf-8')}"
            except Exception as e:
                print(f"Error encoding profile picture: {e}")
                data['profile_picture'] = None
        else:
            data['profile_picture'] = None
            
        return data

class CounsellorsReg(db.Model):
    __tablename__ = 'counsellorreg'
    
    Reg_ID = db.Column(db.Integer, primary_key=True)
    Counsellor_id = db.Column(db.Integer, db.ForeignKey('counsellor.Counsellor_id'), nullable=False)
    Reg_Name = db.Column(db.String(length=100), nullable=False)
    Reg_Email = db.Column(db.String(length=100), unique=True, nullable=False)
    Reg_PNo = db.Column(db.String(length=10), nullable=False, unique=True)
    Reg_Date = db.Column(db.Date, nullable=False)
    Reg_Fee = db.Column(db.String(length=40), nullable=False)
    Reg_Payment = db.Column(db.String(length=20), nullable=False)

    def to_dict(self):
        return {
            'id': self.Reg_ID,
            'name': self.Reg_Name,
            'email': self.Reg_Email,
            'phone': self.Reg_PNo,
            'date': self.Reg_Date.isoformat() if self.Reg_Date else None,
            'fee': self.Reg_Fee,
            'payment': self.Reg_Payment
        }

class Program(db.Model):
    __tablename__ = 'program'
    Program_id = db.Column(db.Integer, primary_key=True)
    Program_name = db.Column(db.String(length=200), nullable=False)
    Program_description = db.Column(db.Text, nullable=False)
    university_id = db.Column(db.Integer, db.ForeignKey('university.id'), nullable=False)
    duration = db.Column(db.String(length=50))
    career_prospects = db.Column(db.Text)
    requirements = db.Column(db.Text)   
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    university = db.relationship('University', backref='programs')

    def to_dict(self):
        return {
            'id': self.Program_id,
            'name': self.Program_name,
            'description': self.Program_description,
            'university': self.university.name if self.university else None,
            'duration': self.duration,
            'career_prospects': self.career_prospects,
            'requirements': self.requirements
        }

class CourseLibrary(db.Model):
    __tablename__ = 'courselibrary'
    Course_id = db.Column(db.Integer, primary_key=True)
    Course_name = db.Column(db.String(length=200), nullable=False)
    Course_description = db.Column(db.Text, nullable=False)
    career_prospects = db.Column(db.Text) 
    course_picture = db.Column(db.LargeBinary)  
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())