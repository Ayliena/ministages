from app import app, db, login_manager, devel_site
#from app.staticdata import TabColor, TabSex, TabHair
from app.models import User
from app.helpers import checkuser
from flask import render_template, redirect, request, url_for, session
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from werkzeug.security import generate_password_hash
from email.mime.text import MIMEText
import subprocess
import re
import random
import string


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
        return render_template("login_page.html", devsite=devel_site)

    user = load_user(request.form["username"])
    if user is None:
        return render_template("login_page.html", devsite=devel_site, error=True)

    if not user.check_password(request.form["password"]):
        return render_template("login_page.html", devsite=devel_site, error=True)

    login_user(user)

    # store last access
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
    if request.method == "GET":
        # provide the empty page
        return render_template("newuser_page.html", devsite=devel_site)

    # 2nd step of account creation
    cmd = request.form["action"]

    if cmd == "UserNew":
        # check the data and return error if something is wrong
        Username = request.form["u_username"]
        FirstName = request.form["u_firstname"]
        LastName = request.form["u_lastname"]
        emailaddr = request.form["u_email"]

        # check if the user already exists
        theUser = User.query.filter_by(username=Username).first()
        if theUser:
            messages.append([ 3, "Nom d'utilisateur deja utilise"])
        
        # only one account can be associated to an email address
        theUser = User.query.filter_by(Email=emailaddr).first()
        if theUser:
            messages.append([ 3, "Adresse email déjà utilisée, vous pouvez récupérer les informations sur le compte à partir de la page de login" ])

        # if adding, perform a check on the data
        if not messages:
            messages = checkuser(Username, 0, FirstName, LastName, emailaddr, 'x', 'x')

        # note that we create the object to refill the form if needed, this data will not be committed
        newuser = User(username=Username, password_hash='nopassword', usertype=0, FirstName=FirstName, LastName=LastName.upper(), Email=emailaddr)

        if not messages:
            # we can add the user
            newuser.newpwd_token = ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(24))
            db.session.add(newuser)
            db.session.commit()

            # send the email
            msg = MIMEText("Ici le site StagesL3,\n\nVotre nouveau compte est: {}\n\nLe mot de passe peut être généré en suivant ce lien:\nhttps://stagesl3.ipcms.fr/newpwd?token={}\n\nA bientôt".format(newuser.username, newuser.newpwd_token))
            msg["From"] = "noreply@stagesl3.ipcms.fr"
            msg["To"] = emailaddr
            msg["Subject"] = "Votre compte StagesL3"
            msg["Reply-To"] = "PLEASE_DO_NOT_REPLY_TO_THIS_ADDRESS@stagesl3.ipcms.fr"
            sendmail_location = "/usr/sbin/sendmail"
            subprocess.run([sendmail_location, "-t", "-oi"], input=msg.as_bytes())

            return render_template("recuser_page.html", devsite=devel_site, email=emailaddr)

        # in case of any error, regenerate the page
        return render_template("newuser_page.html", devsite=devel_site, msg=messages, newuser=newuser)

    # any other cmd: ignore and return to login
    return render_template("login_page.html", devsite=devel_site)


@app.route("/recreate", methods=["GET", "POST"])
def recoveraccount():
    messages = []
    
    # generate the page for the account recovery and the recovery token
    if request.method == "GET":
        # just provide the page
        return render_template("recuser_page.html", devsite=devel_site, msg=messages)

    cmd = request.form["action"]

    if cmd == 'UserCancel':
        # return to the login
        return render_template("login_page.html", devsite=devel_site)

    # get the email
    emailaddr = request.form["u_email"]

    theUser = User.query.filter_by(Email=emailaddr).first()
    if theUser:
        # generate the token, associate it with the user and send the email
        # kill any existing password
        theUser.password_hash = "nopassword"
        theUser.newpwd_token = ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(24))
        # the token is valid forever
        db.session.commit()

        # send the email
        msg = MIMEText("Ici le site StagesL3,\n\nVotre compte est: {}\n\nUn nouveau mot de passe peut être généré en suivant ce lien:\nhttps://stagesl3.ipcms.fr/newpwd?token={}\n\nA bientôt".format(theUser.username, theUser.newpwd_token))
        msg["From"] = "noreply@stagesl3.ipcms.fr"
        #msg["To"] = "ishark@free.fr"
        #msg["To"] = "alberto.barsella@ipcms.unistra.fr"
        msg["To"] = emailaddr
        msg["Subject"] = "Votre compte StagesL3"
        msg["Reply-To"] = "PLEASE_DO_NOT_REPLY_TO_THIS_ADDRESS@stagesl3.ipcms.fr"
        sendmail_location = "/usr/sbin/sendmail"
        subprocess.run([sendmail_location, "-t", "-oi"], input=msg.as_bytes())
            
        return render_template("recuser_page.html", devsite=devel_site, email=emailaddr)

    else:
        # indicate that the email was not found
        messages.append([ 3, "Adresse mail non trouvée"])

    return render_template("recuser_page.html", devsite=devel_site, msg=messages)


@app.route("/newpwd", methods=["GET"])
def newpassword():
    # validate token and regen a random password
    token = request.args.get('token')

    if token:
        # find which user this token is associated to
        theUser = User.query.filter_by(newpwd_token=token).first()
        if theUser:
            # generate a new random password and show it
            newpwd = ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(10))
            theUser.newpwd_token = None
            theUser.password_hash = generate_password_hash(newpwd)
            db.session.commit()

            return render_template("login_page.html", devsite=devel_site, newpassword=newpwd)

    return render_template("error_page.html", devsite=devel_site, errormessage="Invalid token")
