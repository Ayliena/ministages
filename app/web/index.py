from app import app, db, login_manager, devel_site
#from app.staticdata import TabColor, TabSex, TabHair
from app.models import User
from app.helpers import checkuser
from flask import render_template, redirect, request, url_for, session
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from werkzeug.security import generate_password_hash
import re


@login_manager.user_loader
def load_user(user_id):
    return User.query.filter_by(username=user_id).first()


@app.route('/', methods=["GET", "POST"])
@app.route('/index', methods=["GET", "POST"])
def index():
    return redirect(url_for('mainpage'))


@app.route("/login/", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login_page.html", devsite=devel_site, error=False, newuser=False)

    user = load_user(request.form["username"])
    if user is None:
        return render_template("login_page.html", devsite=devel_site, error=True, newuser=False)

    if not user.check_password(request.form["password"]):
        return render_template("login_page.html", devsite=devel_site, error=True, newuser=False)

    login_user(user)

    # store last access and fix number of cats (just in case...)
    current_user.LastOp = datetime.now()
    db.session.commit()

    return redirect(url_for('mainpage'))


@app.route("/logout/")
@login_required
def logout():
    logout_user()
    return redirect(url_for('mainpage'))


@app.route("/create", methods=["GET", "POST"])
def createaccount():
    if request.method == "POST":
        # 2nd step of account creation
        # for the moment, WE DON'T USE EMAIL VALIDATION

        cmd = request.form["action"]

        if cmd == "UserSave":
        # check the data and return error if something is wrong
            Username = request.form["u_username"]
            FirstName = request.form["u_firstname"]
            LastName = request.form["u_lastname"]
            Email = request.form["u_email"]
            pw1 = request.form["u_password1"]
            pw2 = request.form["u_password2"]

            # perform an initial check
            messages = checkuser(Username, 0, FirstName, LastName, Email, pw1, pw2, 0)
            # note that we create the object to refill the form if needed
            newuser = User(username=Username, password_hash=generate_password_hash(pw1), usertype=0, FirstName=FirstName, LastName=LastName.upper(), Email=Email, Phase=1)

            if not messages:
                # check if the user already exists
                theUser = User.query.filter_by(username=Username).first()
                if theUser:
                    messages.append([ 3, "Nom d'utilisateur deja utilise"])

                else:
                    # we can add the user
                    db.session.add(newuser)
                    db.session.commit()

            if messages:
                return render_template("newuser_page.html", devsite=devel_site, msg=messages, newuser=newuser)

            return render_template("login_page.html", devsite=devel_site, error=False, newuser=True)

        else:
            # any other cmd: ignore and return to login
            return render_template("login_page.html", devsite=devel_site, error=False, newuser=False)

    return render_template("newuser_page.html", devsite=devel_site)
