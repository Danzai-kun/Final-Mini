from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class UserSignUp(db.Model):
    Client_ID = db.Column(db.Integer, primary_key=True)
    Client_Name = db.Column(db.String(length=200), nullable=False)
    Client_Email = db.Column(db.String(length=100), unique=True, nullable=False)
    Client_Password = db.Column(db.String(length=200), nullable=False, unique = True)

class Program(db.Model):
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
            'university': self.university,
            'duration': self.duration,
            'career_prospects': self.career_prospects,
            'requirements': self.requirements
        }
        

class Student(db.Model):
    Student_Email = db.Column(db.String(100), primary_key=True)
    Student_Fname = db.Column(db.String(100), nullable=False)
    Student_Lname = db.Column(db.String(100), nullable=False)
    Student_DOB = db.Column(db.Date, nullable=False)
    Student_Phone = db.Column(db.String(20), nullable=False)
    # Relationship with Qualification
    qualification = db.relationship('Qualification', backref='student', uselist=False)

class Qualification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key referencing Student
    student_email = db.Column(db.String(100), db.ForeignKey('student.Student_Email'), unique=True, nullable=False)
    # Foreign key referencing Program
    program_id = db.Column(db.Integer, db.ForeignKey('program.Program_id'), nullable=False)
    class10_percentage = db.Column(db.Float, nullable=False)
    class12_percentage = db.Column(db.Float, nullable=False)
    class12_stream = db.Column(db.String(50), nullable=False)
    class10_Yearpass = db.Column(db.Date, nullable=False)
    class12_Yearpass = db.Column(db.Date, nullable=False)
    class12_Board = db.Column(db.String(100), nullable=False)
    
    # Add relationship to Program
    program = db.relationship('Program', backref='qualifications')
    
class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    
class Counsellor(db.Model):
    __tablename__ = 'counsellor'
    Counsellor_id = db.Column(db.Integer, primary_key=True)
    counsellor_name = db.Column(db.String(100), nullable=False)
    counsellor_email = db.Column(db.String(120), unique=True, nullable=False)
    counsellor_Pno = db.Column(db.String(20), unique=True, nullable=False)
    counsellor_description = db.Column(db.Text)
    counsellor_password = db.Column(db.String(255), nullable=False)
    profile_picture = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    registrations = db.relationship('CounsellorsReg', backref='counsellor', lazy=True)


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
    
class University(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    ranking = db.Column(db.Integer)
    admission_requirements = db.Column(db.Text)
    admission_deadline = db.Column(db.Date)
    career_prospects = db.Column(db.Text)