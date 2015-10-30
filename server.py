from flask import Flask, render_template, redirect, url_for, request, flash
from model import db, connect_to_db, User

app = Flask(__name__)


@app.route('/')
def landing_page():
    """Homepage"""
    # # If not logged in, redirect to log in page, else sent to dashboard
    # if not session.get('user_id'):
    #     return redirect("/login")
    # else:
    #     return redirect("/dashboard")
    return "Homepage"


@app.route("/register")
def register_page():
    """Serving registration form"""

    return render_template('register.html')


@app.route("/register-process", methods=['POST', 'GET'])
def register_process():
    """Add user to database. login_submit"""

    user = User(email=request.form['email'], password=request.form['password'], zipcode=request.form['zipcode'], street_address=request.form['address'])

    db.session.add(user)
    db.session.commit()

    return "register successful!"
    # flash('User successfully registered')
    # return redirect(url_for('to home or??'))



@app.route('/logout')
def logout():
    """ Logout """

    session.clear()
    flash("Logged out")
    return render_template("landing.html")      








if __name__ == "__main__":
    # We have to set debug=True here, since it has to be True at the point
    # that we invoke the DebugToolbarExtension
    app.debug = True

    connect_to_db(app)

    # Use the DebugToolbar
    # DebugToolbarExtension(app)

    app.run()