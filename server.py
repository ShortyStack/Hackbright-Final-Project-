from flask import Flask, render_template, redirect, url_for, request, flash, session
from model import db, connect_to_db, User
from flask_debugtoolbar import DebugToolbarExtension
from jinja2 import StrictUndefined

app = Flask(__name__, static_folder='static')

# If you want to generate random key, go into Python and type:
# >>> import os
# >>> os.urandom(24)
app.secret_key = "&\xd9\x9d\x14\x0b\xa7\xdc\xa1fJ;\xa2-\xff\xc9\x9fdh\xfc.\xa9\xdf\xc1\x99"


@app.route("/")
def homepage():
    """ This is the homepage """

    return render_template("homepage.html")


@app.route("/register", methods=["GET"])
def registration_form():
    """Process login"""

    return render_template("register.html")


@app.route("/register-process", methods=['POST'])
def register_process():
    """Add user to database. login_submit"""
    # inputs form the form checking the db to see if user is in DB already
    email = request.form['email']
    password = request.form['password']
    zipcode = request.form['zipcode']
    street_address = request.form['address']

    print "register-process", email, password, zipcode, street_address

    new_user = User(email=email, password=password, zipcode=zipcode, street_address=street_address)

    same_email_user = User.query.filter(User.email == email).first()

    if same_email_user:
        flash("email already registered")
        return redirect("/login")

    db.session.add(new_user)
    db.session.commit()

    # user = User.query.filter_by(email=email).first()

    flash("You have created your account")
    session["user_id"] = new_user.user_id

    return redirect("/")


####################Login Page ################################################


@app.route("/login", methods=["GET"])
def login_form():
    """Process login"""

    return render_template("login_form.html")


@app.route("/login-process", methods=['POST'])
def login_process():
    """log user into site"""

    email = request.form.get("email")
    print email
    password = request.form.get('password')
    print password

    user = User.query.filter_by(email=email).first()
    print user
    # print user.user_id

    if not user:
        flash("No such user")
        return redirect("/login")

    if user.password != password:
        flash("incorrect password")
        return redirect("/login")
    else:
        session["user_id"] = user.user_id

    flash("Logged in")
    return redirect("/homepage")


############################################################################

@app.route("/step_2", methods=["GET"])
def choose_genre():
    """ User chooses genre """
    # User chooses a genre from the dropdown.

    return render_template("step_2_genre_and_food.html")


@app.route('/step_3', methods=["POST"])
def submit_genre_choice():
    """ Submitting genre choice """
    # After user submits genre choice, a movie is randomly chosen for them.
    return render_template("step_3_get_movie.html")


@app.route("/step_2", methods=["GET"])
def input_address():
    """ User inputs their address """

    return render_template("step_2_genre_and_food.html")


@app.route("/order_food", methods=["POST"])
def submit_address_for_food_order():
    """ Submitting address for food delivery """

    return render_template("order_food.html")


def main():
        # We have to set debug=True here, since it has to be True at the point
    # that we invoke the DebugToolbarExtension
    app.debug = True

    # Raise error if Jinja encounters a problem
    app.jinja_env.undefined = StrictUndefined

    # Connect to the database
    connect_to_db(app)

    # Use the DebugToolbar
    DebugToolbarExtension(app)

    # Start the webserver
    app.run()


if __name__ == "__main__":
    main()
