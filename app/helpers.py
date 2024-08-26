from app import app, db
from email.mime.text import MIMEText
import subprocess
import re

# --------------- HELPER FUNCTIONS

def checkemail(addr):
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'

    return re.fullmatch(regex, addr)


# perform some basic validity checks on user data
def checkuser(username, usertype, firstname, lastname, email, pw1, pw2):
    messages = []

    if not username:
        messages.append([ 3, "Nom d'utilisateur vide"])

    if usertype < 0 and usertype > 2:
        messages.append([ 3, "Type d'utilisateur non valide"])

    if not firstname:
        messages.append([ 3, "Prenom vide"])

    if not lastname:
        messages.append([ 3, "Nom vide"])

    if not email:
        messages.append([ 3, "Adresse e-mail vide"])
    if not checkemail(email):
        messages.append([ 3, "Adresse e-mail non valable"])

    if not pw1 or pw1 != pw2:
        messages.append([ 3, "Les deux mot de passe ne coincident pas ou sont vides"])

    return messages


# send an email to a student to indicate something
# mtype = 10 -> associated to a stage
# mtype = 11 -> deassociated from a stage
# mtype = 12 -> associated to a stage and detached from previous one
# mtype = 20 -> validation from scol and admin
def emailStudent(student, mtype):
    sendmail_location = "/usr/sbin/sendmail"

    # generate the apprpriate mail message
    if mtype == 10 or mtype == 12:
        msg = MIMEText("Ici le site StagesL3,\n\nLe maitre de stage: {} {} <{}> vous a associé à son sujet: \"{}\".{}\n\nPensez à vous connecter au site pour continuer le processus.".format(student.stage.supervisor.FirstName, student.stage.supervisor.LastName, student.stage.supervisor.Email, student.stage.Title, ("(ceci vous a dissocié d'un sujet de stage precedemment choisi)" if mtype == 12 else "")))
        msg["Subject"] = "StagesL3: associé à un stage"

    elif mtype == 11:
        msg = MIMEText("Ici le site StagesL3,\n\nVotre nom a été dissocié du sujet de stage.\n(Si cet evenement est une suprise, il faut penser à recontacter le maitre de stage pour comprendre ce qui s'est passé)")
        msg["Subject"] = "StagesL3: dissocié d'un stage"

    elif mtype == 20:
        # only send the message if everything is valid
        if student.ValidScol and student.ValidAdmin:
            msg = MIMEText("Ici le site StagesL3,\n\nVotre fiche logistique a été validée par un responsable d'UE et par la scolarité\n\nPensez à vous connecter au site pour continuer le processus.")
            msg["Subject"] = "StagesL3: fiche logistique validée"
        else:
            mtype = False   # don't send

    else:
        mtype = False  # don't send

    if mtype:
    # generate the header
        msg["From"] = "noreply@stagesl3.ipcms.fr"
        msg["To"] = student.Email
        msg["Reply-To"] = "PLEASE_DO_NOT_REPLY_TO_THIS_ADDRESS@stagesl3.ipcms.fr"
        # send the email
        subprocess.run([sendmail_location, "-t", "-oi"], input=msg.as_bytes())
