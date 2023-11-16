from app import app, db, devel_site
from app.staticdata import ACC_STUDENT, ACC_SUPERV, ACC_SCOL, ACC_ADMIN
from app.models import User, Stage, GlobalData
from app.helpers import checkuser
from flask import render_template, redirect, request, url_for, session, Response
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

    if cmd == "UserManage" and current_user.usertype == ACC_ADMIN:
        # switch the view to userlist mode
        session["otherMode"] = "usermanage"
        return redirect(url_for('mainpage'))

    if cmd == "StageManage" and (current_user.usertype == ACC_ADMIN or current_user.usertype == ACC_SCOL):
        # switch the view to stage manage mode
        session["otherMode"] = "stagemanage"
        return redirect(url_for('mainpage'))

    if cmd == "MainPage":
        # whatever we are or were, return to the default view
        if "otherMode" in session:
            session.pop("otherMode")
        return redirect(url_for('mainpage'))

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

        if uid == -1:
            # new user
            un = request.form["u_username"]

            # note that passwords are not checked here
            messages = checkuser(un, utype, fn, ln, em, 'a', 'a')

            # handle the password stuff
            if pw1 == "" or pw1 == "random":
                alphabet = string.ascii_letters + string.digits
                pw1 = ''.join(secrets.choice(alphabet) for i in range(8))

            else:
                if pw1 != pw2:
                    messages.append([ 3, "Les deux mot de passe ne coïncident pas"])

            # generate the object, in case we have to regen the page
            newuser = User(username=un, usertype=utype, password_hash=generate_password_hash(pw1), FirstName=fn, LastName=ln.upper(), Email=em, stage_id=None)

            if messages:
                # errors, data will not be saved and we regen the page
                newuser.id = -1
                return render_template("user_page.html", devsite=devel_site, user=current_user, msg=messages, gdata=gendata, edituser=newuser)

            # generate new user
            db.session.add(newuser)

            session["pendingmessages"] = [ [0, "Utilisateur {} crée avec mot de passe = {}".format(un, pw1) ] ]

        else:
            # check the data (except username which is already defined and password, checked later)
            messages = checkuser('xxx', utype, fn, ln, em, 'a', 'a')

            # update user
            theUser = User.query.filter_by(id=uid).first()
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

        db.session.commit()
        return redirect(url_for('mainpage'))

    if cmd == "UserCancel" and current_user.usertype == ACC_ADMIN:
        # just return to the previous page
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
            session["pendingmessages"] = [ [0, "Utilisateur effacé"] ]
        else:
            session["pendingmessages"] = [ [3, "Cet utilisateur ne peut pas être effacé"] ]

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
                if len(request.files['s_pdf'].filename) > 124:
                    messages.append([3, "Nom du fichier trop long... utiliser moins de 120 caracteres, svp!"])

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
                # now save the new one
                pdf_file = request.files['s_pdf']
                if pdf_file:
                    # delete previous one
                    if sujet.PDFfile:
                        if os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], sujet.PDFfile)):
                            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], sujet.PDFfile))

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
        # note that all confirmed students will not appear anywhere
        students1 = User.query.filter(and_(User.usertype==ACC_STUDENT, User.stage_id==None)).all()
        students2 = User.query.filter(and_(and_(User.usertype==ACC_STUDENT, User.stage_id!=None),User.PDFfiche==None)).all()

        return render_template("stage_page.html", devsite=devel_site, user=current_user, gdata=gendata, stage=sujet, studns=students1, studs=students2, subjattach=True)

    if cmd.startswith('SubjAttach-') and current_user.usertype == ACC_SUPERV:
        # attach a student to a subject
        sid = int(request.form["s_id"])
        sujet = Stage.query.filter_by(id=sid).first()
        if not sujet or sujet.supervisor_id != current_user.id:
            return render_template("error_page.html", devsite=devel_site, user=current_user, errormessage="invalid sujet id")

        # get the student
        stid = int(cmd[11:])
        student = User.query.filter_by(id=stid).first()
        if not student or student.usertype != ACC_STUDENT:
            return render_template("error_page.html", devsite=devel_site, user=current_user, errormessage="invalid student id")

        # make sure the student is not already attached (if yes, ignore)
        # make sure the student is not "confirmed"
        if student.stage_id != sujet.id and not student.PDFfiche:
            # in case we're switching stage, we need to remove the student from the count of the other stage
            if student.stage_id:
                sujet2 = Stage.query.filter_by(id=student.stage_id).first()
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
        # detach a student from a subject
        sid = int(request.form["s_id"])
        sujet = Stage.query.filter_by(id=sid).first()
        if not sujet:
            return render_template("error_page.html", devsite=devel_site, user=current_user, errormessage="invalid sujet id")

        # get the student
        stid = int(cmd[11:])
        student = User.query.filter_by(id=stid).first()
        if not student or student.usertype != ACC_STUDENT:
            return render_template("error_page.html", devsite=devel_site, user=current_user, errormessage="invalid student id")

        # detach is only possible if the fiche logistique was NOT submitted
        if student.PDFfiche:
            return render_template("error_page.html", devsite=devel_site, user=current_user, errormessage="fiche logistique uploaded, can't detach")

        # if the student is not attached, ignore, otherwise detach
        if student.stage_id == sujet.id:
            student.stage_id = None
            sujet.NStudents = sujet.NStudents - 1
            db.session.commit()

        return redirect(url_for('mainpage'))

    if cmd == "StudFiche" and current_user.usertype == ACC_STUDENT:
        # save the PDF file
        messages = []

        # note that for a new subject a PDF MUST be provided
        if not 's_pdf' in request.files or not request.files['s_pdf']:
            messages.append([3, "Fichier PDF non fourni"])

        else:
            ext = request.files['s_pdf'].filename[-4:]
            if not ext.upper() == ".PDF":
                messages.append([3, "Le fichier n'est pas un PDF"])

        # if no errors, save the file
        if not messages:
            # if a file is provided, save it
            # in case we already had a file, erase the old one first
            if current_user.PDFfiche:
                if os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], current_user.PDFfiche)):
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], current_user.PDFfiche))

            # now save the new one
            pdf_file = request.files['s_pdf']
            if pdf_file:
                filename = secure_filename(pdf_file.filename)
                filename = "{}-{}".format(current_user.id, filename)
                pdf_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                current_user.PDFfiche = filename

                # note that this resets any validation
                current_user.ValidAdmin = False
                current_user.ValidScol = False

            current_user.LastOp = datetime.now()
            db.session.commit()
        else:
            # errors are present, regen the page
            return render_template("student_page.html", devsite=devel_site, user=current_user, msg=messages, gdata=gendata)

        return redirect(url_for('mainpage'))

    if cmd.startswith("ScolValid-") and current_user.usertype == ACC_SCOL:
        uid = int(cmd[10:])
        # find the user
        student = User.query.filter_by(id=uid).first()

        if not student or student.usertype != ACC_STUDENT or not student.PDFfiche:
            return render_template("error_page.html", devsite=devel_site, user=current_user, errormessage="validation: user state error")

        student.ValidScol = True
        db.session.commit()
        return redirect(url_for('mainpage'))

    if cmd.startswith("AdminValid-") and current_user.usertype == ACC_ADMIN:
        uid = int(cmd[11:])
        # find the user
        student = User.query.filter_by(id=uid).first()

        if not student or student.usertype != ACC_STUDENT or not student.PDFfiche:
            return render_template("error_page.html", devsite=devel_site, user=current_user, errormessage="validation: user state error")

        student.ValidAdmin = True
        db.session.commit()
        return redirect(url_for('mainpage'))

    if cmd == "DataExport" and (current_user.usertype == ACC_ADMIN or current_user.usertype == ACC_SCOL):
        # generate a CSV file with the current status
        csv="Etudiant,,Stage,Maître de Stage,,Fiche Logistique,Validee Scol.,Validee Resp.\n"

        # first part is table by student
        students = User.query.filter_by(usertype=ACC_STUDENT).all()

        for st in students:
            csv += ('"'+st.LastName+' '+st.FirstName+'",'+st.Email+',')
            if st.stage:
                ti = st.stage.Title
                ti.replace('"', '\"')
                csv += ('"'+ti+'","'+st.stage.supervisor.LastName+" "+st.stage.supervisor.FirstName+'",'+st.stage.supervisor.Email)

                if st.PDFfiche:
                    csv += ",OUI" + (",OUI" if st.ValidScol else ",non") + (",OUI" if st.ValidAdmin else ",non")
                else:
                    csv += ",non"

            csv += "\n"

        csv += "\n\nMaitre de Stage,,Stage,Etudiants\n"

        stages = Stage.query.filter_by(Obsolete=False).all()

        for sj in stages:
            ti = sj.Title
            ti.replace('"', '\"')
            csv += ('"'+sj.supervisor.LastName+" "+sj.supervisor.FirstName+'",'+sj.supervisor.Email+',"'+ti+'"')

            for st in sj.students:
                csv += ',"'+st.LastName+" "+st.FirstName+'"'
            csv += "\n"

        return Response(
            csv,
            mimetype="text/csv",
            headers={"Content-disposition":
                     "attachment; filename=stagesL3.csv"})

    # default is return to index
    #return redirect(url_for('fapage'))

    return render_template("error_page.html", devsite=devel_site, user=current_user, errormessage="invalid command")
