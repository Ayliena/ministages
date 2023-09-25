from app import app, db
from app.models import User, GlobalData
#from socket import gethostname
from werkzeug.security import generate_password_hash
import string
import secrets
#from datetime import datetime

if __name__ == '__main__':
#    file = open("testfile.txt", "w")
#    file.write("Now is {}\n".format(datetime.now()))
#    file.close()

    print("--- command-line exec mode ---")
    print("Generating db....")
    db.create_all()
    print("Populating with default users....");

    # add myself as admin with a password
    userADM = User.query.filter_by(username="abarsella").first()
    if not userADM:
        alphabet = string.ascii_letters + string.digits
        password = ''.join(secrets.choice(alphabet) for i in range(8))

        print("--> admin is abarsella/{}".format(password))
        newuser = User(username="abarsella", password_hash=generate_password_hash(password), usertype=2, FirstName="Alberto", LastName="BARSELLA", Email="alberto.barsella@ipcms.unistra.fr")
        db.session.add(newuser)
        globaldata = GlobalData(Phase=0)
        db.session.add(globaldata)
    else:
        # regenerate my password
        alphabet = string.ascii_letters + string.digits
        password = ''.join(secrets.choice(alphabet) for i in range(8))
        print("--> admin is abarsella/{}".format(password))
        userADM.password_hash = generate_password_hash(password)
        userADM.usertype = 2

    db.session.commit()

#    if 'liveconsole' not in gethostname():
#        app.run()
