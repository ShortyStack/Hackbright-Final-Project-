from flask import Flask, render_template, redirect, url_for, request, flash
from model import db, connect_to_db, User

app = Flask(__name__)

app.secret_key = "banana"


@app.route('/')
def landing_page():
    """Homepage"""
    # # If not logged in, redirect to log in page, else sent to dashboard
    # if not session.get('user_id'):
    #     return redirect("/login")
    # else:
    #     return redirect("/dashboard")
    return render_template("homepage.html")


# @app.route("/register")
# def register_page():
#     """Serving registration form"""

#     return render_template('register.html')


@app.route("/register-process", methods=['POST', 'GET'])
def register_process():
    """Add user to database. login_submit"""

    user = User(email=request.form['email'], password=request.form['password'], zipcode=request.form['zipcode'], street_address=request.form['address'])

    db.session.add(user)
    db.session.commit()

    return "register successful!"
    flash('User successfully registered')
    return redirect(url_for("homepage.html"))


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
    print user.user_id

    if not user:
        flash("No such user")
        return redirect("/login")

    if user.password != password:
        flash("incorrect password")
        return redirect("/login")

    session["user_id"] = user.user_id

    flash("Logged in")
    return redirect("/users/%s" % user.user_id)

    return "Monsters are cool"





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













if __name__ == "__main__":
    # We have to set debug=True here, since it has to be True at the point
    # that we invoke the DebugToolbarExtension
    app.debug = True

    connect_to_db(app)

    # Use the DebugToolbar
    # DebugToolbarExtension(app)

    app.run()