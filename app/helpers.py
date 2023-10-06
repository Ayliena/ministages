from app import app, db
import re

# --------------- HELPER FUNCTIONS

def checkemail(addr):
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'

    return re.fullmatch(regex, addr)


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
