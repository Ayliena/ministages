from app import db
from werkzeug.security import check_password_hash
from flask_login import UserMixin
from datetime import datetime

class Stage(db.Model):

    __tablename__ = "stages"

    id = db.Column(db.Integer, primary_key=True)
    supervisor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
#    supervisor = db.relationship('User', foreign_keys=supervisor_id)
    students = db.relationship('User', backref='stage', foreign_keys='User.stage_id', lazy=True)
    NStudents = db.Column(db.Integer)
    PDFfile = db.Column(db.String(128))
    Title = db.Column(db.String(256))
    LastOp = db.Column(db.DateTime)
    Obsolete = db.Column(db.Boolean)

class User(UserMixin, db.Model):

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    newpwd_token = db.Column(db.String(32))
    usertype = db.Column(db.Integer)
    FirstName = db.Column(db.String(64), nullable=False)
    LastName = db.Column(db.String(64), nullable=False)
    Email = db.Column(db.String(128))
    LastOp = db.Column(db.DateTime)
    # only valid for a student
    stage_id = db.Column(db.Integer, db.ForeignKey('stages.id'))
#    stage = db.relationship('Stage', foreign_keys=stage_id)
    PDFfiche = db.Column(db.String(128))
    ValidAdmin = db.Column(db.Boolean)
    ValidScol = db.Column(db.Boolean)
    # non-empty only for supervisors
    subjects = db.relationship('Stage', backref='supervisor', foreign_keys=[Stage.supervisor_id], lazy=True)
    # only valid for students
    evaluation_id = db.Column(db.Integer, db.ForeignKey('evaluations.id'))
#    evaluation = db.relationship('Evaluation', foreign_keys=evaluations_id)
    
    def __repr__(self):
        return "<User {}={} {}>".format(self.username, self.FirstName, self.LastName)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return self.username

class Evaluation(db.Model):
    __tablename__ = "evaluations"

    id = db.Column(db.Integer, primary_key=True)

    EvalDate = db.Column(db.DateTime)
    Absence = db.Column(db.Boolean)
    AbsenceText = db.Column(db.String(512))
    StBiblio = db.Column(db.String(1024))
    StInfo = db.Column(db.String(1024))
    StExp = db.Column(db.String(1024))
    StTh = db.Column(db.String(1024))
    Work = db.Column(db.Integer)
    Know = db.Column(db.Integer)
    Indi = db.Column(db.Integer)
    Init = db.Column(db.Integer)
    Rigr = db.Column(db.Integer)
    RepRead = db.Column(db.Boolean)
    RepReadN = db.Column(db.Integer)
    Comments = db.Column(db.String(1024))
    student = db.relationship('User', backref='evaluation', foreign_keys='User.evaluation_id', lazy=True)

class GlobalData(db.Model):

    __tablename__ = "globaldata"

    id = db.Column(db.Integer, primary_key=True)
    PhaseMdS = db.Column(db.Integer)
