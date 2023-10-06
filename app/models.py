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
    usertype = db.Column(db.Integer)
    FirstName = db.Column(db.String(64), nullable=False)
    LastName = db.Column(db.String(64), nullable=False)
    Email = db.Column(db.String(128))
    LastOp = db.Column(db.DateTime)
    stage_id = db.Column(db.Integer, db.ForeignKey('stages.id'))
#    stage = db.relationship('Stage', foreign_keys=stage_id)
    PDFfiche = db.Column(db.String(128))
    ValidAdmin = db.Column(db.Boolean)
    ValidScol = db.Column(db.Boolean)
    subjects = db.relationship('Stage', backref='supervisor', foreign_keys=[Stage.supervisor_id], lazy=True)

    def __repr__(self):
        return "<User {}={} {}".format(self.username, self.FirstName, self.LastName)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return self.username

class GlobalData(db.Model):

    __tablename__ = "globaldata"

    id = db.Column(db.Integer, primary_key=True)
    Phase = db.Column(db.Integer)
