from app import app, db, devel_site
from app.staticdata import ACC_STUDENT, ACC_SUPERV, ACC_ADMIN
from app.models import User, Stage, GlobalData
# from app.helpers import cat_delete, isFATemp, isRefuge, getViewUser, accessPrivileges
from flask import render_template, redirect, request, url_for, session
from flask_login import login_required, current_user
from datetime import datetime

@app.route('/main', methods=["GET", "POST"])
def mainpage():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    # get generic configuration data
    gendata = GlobalData.query.first()

    # decide which type of page to display
    mode = None
    if "otherMode" in session:
        mode = session["otherMode"]

    if "pendingmessages" in session:
        messages = session["pendingmessages"]
        session.pop("pendingmessages")
    else:
        messages = []

    # generate the page depending on user type
    if current_user.usertype == ACC_STUDENT:
        if mode == "subjlist":
            # list the subjects, so that you know them
            return render_template("stage_page.html", devsite=devel_site, user=current_user, gdata=gendata, stages=Stage.query.all())

        return render_template("student_page.html", devsite=devel_site, user=current_user, gdata=gendata)

    if current_user.usertype == ACC_SUPERV:
        # get all subjets for this supervisor
        subjects = Stage.query.all()

        # subjects = Stage.query.filter_by(owner_id=current_user.id)
        return render_template("supervisor_page.html", devsite=devel_site, user=current_user, gdata=gendata, subs=subjects)

    if current_user.usertype == ACC_ADMIN:
        # use the session variable to determine the type of page (main / userlist)
        if mode == "userlist":
            # generate the userlist for user management
            users = User.query.all()
            return render_template("user_page.html", devsite=devel_site, user=current_user, userlist=users, gdata=gendata, msg=messages)

        return render_template("admin_page.html", devsite=devel_site, user=current_user, gdata=gendata, msg=messages)

    return render_template("error_page.html", devsite=devel_site, user=current_user, errormessage="invalid user type")
