from app import app, db, devel_site
from app.staticdata import ACC_STUDENT, ACC_SUPERV, ACC_ADMIN
from app.models import User, Stage, GlobalData
from app.helpers import checkuser
from flask import render_template, redirect, request, url_for, session
from flask_login import login_required, current_user
from sqlalchemy import and_
from datetime import datetime
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
import string
import secrets
import os

@app.route('/edit', methods=["POST"])
def editpage():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    # get generic configuration data
    gendata = GlobalData.query.first()

    # handle the actions
    if request.method == "POST":
        cmd = request.form["action"]

    else:
       return redirect(url_for('main'))

    # create new user, step 1 empty page
    if cmd == "UserAdd" and current_user.usertype == ACC_ADMIN:
        # generate empty page
        return render_template("user_page.html", devsite=devel_site, user=current_user, gdata=gendata)

    if cmd == "UserSave" and current_user.usertype == ACC_ADMIN:
        # check for new or update
        uid = int(request.form["u_id"])
        fn = request.form["u_firstname"]
        ln = request.form["u_lastname"]
        em = request.form["u_email"]
        pw1 = request.form["u_password1"]
        pw2 = request.form["u_password2"]
        utype = int(request.form["u_type"])
        uphase = int(request.form["u_phase"])

        if uid == -1:
            # new user
            un = request.form["u_username"]

            # note that passwords are not checked here
            messages = checkuser(un, utype, fn, ln, em, 'a', 'a', uphase)

            # handle the password stuff
            if pw1 == "" or pw1 == "random":
                alphabet = string.ascii_letters + string.digits
                pw1 = ''.join(secrets.choice(alphabet) for i in range(8))

            else:
                if pw1 != pw2:
                    messages.append([ 3, "Les deux mot de passe ne coincident pas"])

            # generate the object, in case we have to regen the page
            newuser = User(username=un, usertype=utype, password_hash=generate_password_hash(pw1), FirstName=fn, LastName=ln.upper(), Email=em, stage_id=None, Phase=uphase)

            if messages:
                # errors, data will not be saved and we regen the page
                newuser.id = -1
                return render_template("user_page.html", devsite=devel_site, user=current_user, msg=messages, gdata=gendata, edituser=newuser)

            # generate new user
            db.session.add(newuser)

            session["pendingmessages"] = [ [0, "Utilisateur {} cree avec mot de passe = {}".format(un, pw1) ] ]

        else:
            # check the data (except username which is already defined and password, checked later)
            messages = checkuser('xxx', utype, fn, ln, em, 'a', 'a', uphase)

            # update user
            theUser = User.query.filter_by(id=uid).first();
            if not theUser:
                render_template("error_page.html", devsite=devel_site, user=current_user, errormessage="invalid user id")

            # handle the password stuff
            if pw1 == "random":
                alphabet = string.ascii_letters + string.digits
                pw1 = ''.join(secrets.choice(alphabet) for i in range(8))

                session["pendingmessages"] = [ [0, "Mot de passe = "+ pw1 ] ]

            theUser.FirstName = fn
            theUser.LastName = ln.upper()
            theUser.Email = em
            if pw1:
                theUser.password_hash=generate_password_hash(pw1)
            theUser.usertype = utype
            theUser.Phase = uphase

        db.session.commit()
        return redirect(url_for('mainpage'))

    if cmd == "UserCancel" and current_user.usertype == ACC_ADMIN:
        # just return to the previous page
        return redirect(url_for('mainpage'))

    if cmd == "UserManage" and current_user.usertype == ACC_ADMIN:
        # switch the view to userlist mode
        session["otherMode"] = "userlist"
        return redirect(url_for('mainpage'))

    if cmd == "MainPage":
        # whatever we are or were, return to the default view
        session.pop("otherMode")
        return redirect(url_for('mainpage'))

    # handle the edit-XXX commands
    if cmd.startswith('edit-') and current_user.usertype == ACC_ADMIN:
        # get the id
        uid = int(cmd[5:])
        euser = User.query.filter_by(id=uid).first()
        if euser:
            return render_template("user_page.html", devsite=devel_site, user=current_user, gdata=gendata, edituser=euser)

        return redirect(url_for('mainpage'))

    # handle the del-XXX commands
    if cmd.startswith('del-') and current_user.usertype == ACC_ADMIN:
        # get the id
        uid = int(cmd[4:])
        deluser = User.query.filter_by(id=uid).first()
        if deluser and deluser.usertype != 2:
            db.session.delete(deluser)
            db.session.commit()
            session["pendingmessages"] = [ [0, "Utilisateur efface"] ]
        else:
            session["pendingmessages"] = [ [3, "Cet utilisateur ne peut pas etre efface"] ]

        return redirect(url_for('mainpage'))

    if cmd == "SubjList" and current_user.usertype == ACC_STUDENT:
        # switch the view to userlist mode
        session["otherMode"] = "subjlist"
        return redirect(url_for('mainpage'))

    if cmd == "SubjAdd" and current_user.usertype == ACC_SUPERV:
        # generate the page for a new stage
        nsubj = Stage(id=-1, supervisor_id=current_user.id, Title="", PDFfile="")
        return render_template("stage_page.html", devsite=devel_site, user=current_user, gdata=gendata, subject=nsubj)

    if cmd == "SubjEdit" and current_user.usertype == ACC_SUPERV:
        # generate the page for an existing stage
        sid = int(request.form["s_id"])
        sujet = Stage.query.filter_by(id=sid).first()
        if not sujet:
            return render_template("error_page.html", devsite=devel_site, user=current_user, errormessage="invalid sujet id")

        return render_template("stage_page.html", devsite=devel_site, user=current_user, gdata=gendata, subject=sujet)

    if cmd == "SubjSave" and current_user.usertype == ACC_SUPERV:
        # generate and save the PDF file and the object
        messages = []

        sid = int(request.form["s_id"])
        ti = request.form["s_title"]
        if not ti:
            messages.append([3, "Titre du sujet vide"])

        # note that for a new subject a PDF MUST be provided
        if sid == -1 and (not 's_pdf' in request.files or not request.files['s_pdf']):
            messages.append([3, "Fichier PDF non fourni"])

        else:
            # check file extension
            if 's_pdf' in request.files and request.files['s_pdf']:
                ext = request.files['s_pdf'].filename[-4:]
                if not ext.upper() == ".PDF":
                    messages.append([3, "Le fichier n'est pas un PDF"])

        if sid == -1:
            sujet = Stage(supervisor_id=current_user.id, NStudents=0, Title=ti)
        else:
            sujet = Stage.query.filter_by(id=sid).first()
            if not sujet:
                return render_template("error_page.html", devsite=devel_site, user=current_user, errormessage="invalid sujet id")
            sujet.Title = ti

        # generate/edit if no errors
        if not messages:
            # if a file is provided, save it
            # in case we already had a file, erase the old one first

            # this is required so that the record has a valid id
            if sid == -1:
                db.session.add(sujet)
                db.session.commit()

            if 's_pdf' in request.files:
                if sujet.PDFfile:
                    if os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], sujet.PDFfile)):
                        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], sujet.PDFfile))

                # now save the new one
                pdf_file = request.files['s_pdf']
                if pdf_file:
                    filename = secure_filename(pdf_file.filename)
                    filename = "{}-{}".format(sujet.id, filename)
                    pdf_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    sujet.PDFfile = filename
                    sujet.Obsolete = False

            sujet.LastOp = datetime.now()

            if sid == -1:
                db.session.add(sujet)
            db.session.commit()
        else:
            # errors are present, regen the page
            # clobber the id if it's a new subject
            if sid == -1:
                sujet.id = -1
            return render_template("stage_page.html", devsite=devel_site, user=current_user, msg=messages, gdata=gendata, subject=sujet)

        return redirect(url_for('mainpage'))

    if cmd == "SubjCancel" and current_user.usertype == ACC_SUPERV:
        # forget about it and return to the main page
        return redirect(url_for('mainpage'))

    if cmd == "SubjErase" and current_user.usertype == ACC_SUPERV:
        # find the stage
        sid = int(request.form["s_id"])
        sujet = Stage.query.filter_by(id=sid).first()
        if not sujet:
            return render_template("error_page.html", devsite=devel_site, user=current_user, errormessage="invalid sujet id")

        if sujet.PDFfile:
            if os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], sujet.PDFfile)):
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], sujet.PDFfile))

        # make sure no student is linking to this
        students = User.query.filter_by(stage_id=sid).all()
        for st in students:
            st.stage_id = None

        db.session.delete(sujet)
        db.session.commit()
        return redirect(url_for('mainpage'))

    if cmd == "SubjAttach" and current_user.usertype == ACC_SUPERV:
        sid = int(request.form["s_id"])
        sujet = Stage.query.filter_by(id=sid).first()
        if not sujet:
            return render_template("error_page.html", devsite=devel_site, user=current_user, errormessage="invalid sujet id")

        if sujet.supervisor_id != current_user.id:
            return render_template("error_page.html", devsite=devel_site, user=current_user, errormessage="stage/supervisor mismatch")

        # generate a table of the students, separating those who already have a stage from those who don't
        students1 = User.query.filter(and_(User.usertype==ACC_STUDENT, User.stage_id==None)).all()
        students2 = User.query.filter(and_(User.usertype==ACC_STUDENT, User.stage_id!=None)).all()

        return render_template("stage_page.html", devsite=devel_site, user=current_user, gdata=gendata, stage=sujet, studns=students1, studs=students2)

    if cmd.startswith('SubjAttach-') and current_user.usertype == ACC_SUPERV:
        # attach a student to a subject
        sid = int(request.form["s_id"])
        sujet = Stage.query.filter_by(id=sid).first()
        if not sujet:
            return render_template("error_page.html", devsite=devel_site, user=current_user, errormessage="invalid sujet id")

        # get the student
        stid = int(cmd[11:])
        student = User.query.filter_by(id=stid).first()
        if not student or student.usertype != ACC_STUDENT:
            return render_template("error_page.html", devsite=devel_site, user=current_user, errormessage="invalid student id")

        # make sure the student is not already attached (if yes, ignore)
        if student.stage_id != sujet.id:
            # in case we're switching stage, we need to remove the student from the count of the other stage
            if student.stage_id:
                sujet2 = Stage.query.filter_by(id=sid).first()
                if not sujet2:
                    # this must not happen, we should report an internal error, but for the moment we just ignore the problem
                    student.stage_id = None
                else:
                    sujet2.NStudents = sujet2.NStudents - 1

            sujet.NStudents = sujet.NStudents + 1
            student.stage_id = sujet.id
            db.session.commit()

        return redirect(url_for('mainpage'))

    if cmd.startswith('SubjDetach-') and current_user.usertype == ACC_SUPERV:
        # attach a student to a subject
        sid = int(request.form["s_id"])
        sujet = Stage.query.filter_by(id=sid).first()
        if not sujet:
            return render_template("error_page.html", devsite=devel_site, user=current_user, errormessage="invalid sujet id")

        # get the student
        stid = int(cmd[11:])
        student = User.query.filter_by(id=stid).first()
        if not student or student.usertype != ACC_STUDENT:
            return render_template("error_page.html", devsite=devel_site, user=current_user, errormessage="invalid student id")

        # if the student is not attached, ignore, otherwise detach
        if student.stage_id == sujet.id:
            student.stage_id = None
            sujet.NStudents = sujet.NStudents - 1
            db.session.commit()

        return redirect(url_for('mainpage'))

    return render_template("error_page.html", devsite=devel_site, user=current_user, errormessage="invalid command")
