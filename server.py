# coding=utf-8
#
# TODO:
# 1. Add more robust error handling (talk to API and web server is down........)  *
# 2. Add modal windows for movie and food execution  ***
# 4. Add geolocation for users food delivery address screen  **
# 5. Testing with unittest
# 6. Custom error pages (404, 500, etc.)
#
# ChangeLog:
# + Got basic MVP working (2015-11-15)
# + Replaced genre section to movie source section. (This is in step_2) (11-16-15)
# + Add non free sources (Amazon, HBO....) (11-17-15)
# + Added event audit logs (user-agent, referrer, client IP address) (11-22-15)
# + Added admin page (add users, delete users, view audit logs) (11-22-15)
# + Added Ajax to display loading animated gif while talking to API's (11-19-15)
# + Deployed to [Heroku] server


"""
Netflix and Chow
Written by: Wendy Zenone (2015-11-14) 
"""


# Import local libraries
import os
from datetime import datetime
from datetime import timedelta
from random import choice

# Import third party libraries
import requests
from flask import Flask, jsonify, render_template, redirect, url_for, request, flash, session
from flask_debugtoolbar import DebugToolbarExtension
from functools import wraps
from jinja2 import StrictUndefined
from model import db, connect_to_db, User, Audit


# Configuration for delivery.com and movie APIs
DELIVERY_API_KEY = os.environ["DELIVERY_ACCESS_TOKEN_KEY"]  # Remember to `source secrets.sh` first
DELIVERY_BASE_API_URL = 'https://api.delivery.com'
DELIVERY_ENDPOINT = '/merchant/search/delivery'
DEFAULT_METHOD = 'delivery'
DEFAULT_MERCHANT_TYPE = 'R'

# Configuration for Guidebox API
GUIDEBOX_API_KEY = os.environ["GUIDEBOX_API_KEY"]
GUIDEBOX_BASE_URL = "https://api-public.guidebox.com/v1.43"
GUIDEBOX_REGION = "US"
GUIDEBOX_API_DIRECTORY = "movies/all"


# Create Flask object
app = Flask(__name__, static_folder='static')

# If you want to generate random key, go into Python and type:
# >>> import os
# >>> os.urandom(24)

app.secret_key = os.environ.get("SECRET_KEY", "testsecretkey")


############################################################################
# Make sure a user is logged in to access protected resources

def login_required(f):
    """ This will require a user to be logged in to access a protected route """

    @wraps(f)
    def decorated_function():
        """
        The function that does the login enforcement
        """
        if not session.get('user_id'):
            audit_event(event="Unauthorized user tried accessing page that requires login")
            return redirect(url_for('homepage'))
        return f()

    return decorated_function


############################################################################
# Admin Helper Function

def admin_required(f):
    """ This will be used to require admin """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        """ The decorator itself """

        if not session.get('admin'):
            audit_event(event="Unauthorized user tried accessing admin page")
            return redirect(url_for('homepage'))
        return f(*args, **kwargs)

    return decorated_function


############################################################################
# Session Timeout

@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=180)


############################################################################
# Homepage

@app.route("/")
def homepage():
    """ This is the homepage """
    if not session.get("user_id"):
        return render_template("/homepage.html")
    else:
        return redirect("/step_2")


############################################################################
# Login

@app.route("/login", methods=["GET"])
def login_form():
    """Process login"""

    return render_template("login_form.html")


@app.route("/login-process", methods=['POST'])
def login_process():
    """log user into site"""

    email = request.form.get("email")
    password = request.form.get('password')

    user = User.query.filter_by(email=email).first()

    if user and user.verify_password(password):
        print "Successful Login: {}".format(email)
        flash("Logged in", 'info')
        session["user_id"] = user.user_id
        session["email"] = user.email
        session["street_address"] = user.street_address
        session["zipcode"] = user.zipcode
        session["first_name"] = user.first_name
        session["last_name"] = user.last_name
        session["admin"] = user.admin
        audit_event(event="User successfully logged in")
        return redirect("/")
    else:
        print "Failed login attempt: {}:{}".format(email, password)
        flash("Invalid login", "info")
        audit_event(event="Failed login attempt ({}:{})".format(email, password))
        return redirect("/")


############################################################################
# Logout

@app.route("/logout")
@login_required
def logout():
    """ User logs out """

    audit_user_id = session["user_id"]
    session.clear()
    # TODO: Audit this event
    flash("You have been logged out", "info")
    audit_event(event="User logged out")
    return redirect("/")


############################################################################
# Register a new account

@app.route("/register", methods=["GET"])
def registration_form():
    """Display account creation page for the user"""

    return render_template("register.html")


@app.route("/register-process", methods=['POST'])
def register_process():
    """Add user to database. login_submit"""

    # inputs form the form checking the db to see if user is in DB already
    # Add the admin
    email = request.form['email']
    password = request.form['password']
    street_address = request.form['address']
    zipcode = request.form['zipcode']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    admin = False

    # Check if this email address has already registered an account
    user = User.query.filter_by(email=email).first()
    print user
    if user:
        flash("Email already registered", "info")
        return redirect("/register")
    else:
        # Otherwise, create the account in the db
        print "Register-process: {}, {}, {}".format(email, street_address, zipcode)
        new_user = User(email=email, street_address=street_address, zipcode=zipcode, first_name=first_name,
                        last_name=last_name, admin=admin)
        new_user.hash_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash("You have created your account", "info")
        session["user_id"] = new_user.user_id
        session["email"] = new_user.email
        session["street_address"] = street_address
        session["zipcode"] = zipcode
        session["first_name"] = first_name
        session["last_name"] = last_name
        session["admin"] = admin
        audit_event(event="New user registered ({})".format(session['email']))
        return redirect("/")


##############################################################################
# Profile

@app.route("/profile", methods=["GET", "POST"])
@login_required
def users_page():
    """Manage user profile"""
    if request.method == 'GET':
        return render_template("/profile.html",
                               first_name=session['first_name'],
                               last_name=session['last_name'],
                               email=session['email'],
                               street_address=session['street_address'],
                               zipcode=session['zipcode'])
    else:
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        new_password_confirm = request.form['new_password_confirm']
        street_address = request.form['street_address']
        zipcode = request.form['zipcode']

        # Load the user's information based upon the email address
        user = User.query.filter(User.email == session['email']).first()

        # Determine if this is just an address change
        if not new_password and not new_password_confirm and user.verify_password(current_password):
            user.street_address = street_address
            user.zipcode = zipcode
            db.session.commit()
            session['street_address'] = street_address
            session['zipcode'] = zipcode
            flash("Address successfully changed.", 'info')
            audit_event(event="User changed address")
            return redirect("/profile")

        # Else, let's assume this includes a password change
        elif user.verify_password(current_password):
            if new_password == new_password_confirm:
                address_update = False
                if session['street_address'] != street_address:
                    user.street_address = street_address
                    address_update = True
                if session['zipcode'] != zipcode:
                    user.zipcode = zipcode
                    address_update = True
                user.hash_password(new_password)
                db.session.commit()
                session['street_address'] = street_address
                session['zipcode'] = zipcode
                if address_update:
                    audit_event(event="User changed address and password")
                    flash("Address and password successfully changed.", 'info')
                else:
                    audit_event(event="User changed password")
                    flash("Password successfully changed.", 'info')
                return redirect("/profile")
            else:
                flash("New passwords do not match.", 'info')
                return redirect("/profile")

        # Otherwise, they entered in the wrong current password.
        else:
            flash("Invalid current password.", 'info')
            return redirect("/profile")


############################################################################
# Administrative

@app.route("/audit_logs", methods=["GET"])
@login_required
@admin_required
def audit_logs():
    """ View Audit Logs """
    audit_event(event="Audit log page accessed")
    return render_template("/view_audit_logs.html")


@app.route("/get_audit_logs", methods=["POST"])
@login_required
@admin_required
def get_audit_logs(page=1, entries=5):
    """  Get the audit logs """

    if 'entries' in request.form:
        entries = int(request.form['entries'])
    else:
        entries = entries
    logs = Audit.query.filter_by().paginate(page=page, per_page=entries)  # Have not gotten to this yet
    data = {
        'config': dict(has_next=logs.has_next, has_prev=logs.has_prev, next_num=logs.next_num, prev_num=logs.prev_num),
        'data': {}}
    for index, log in enumerate(logs.items):
        data['data'][index] = dict(id=log.event_id, utc_timestamp=log.timestamp, user_id=log.user_id, event=log.event,
                                   ip=log.ip, user_agent=log.user_agent)
    return jsonify(data)


@app.route("/users", methods=["GET"])
@login_required
@admin_required
def manage_users_page():
    """ Manage users """
    users = User.query.all()
    audit_event(event="User administration page accessed")
    return render_template("/admin_users.html", users=users)


@app.route("/add_user", methods=["POST"])
@login_required
@admin_required
def add_user():
    """ Add user to db """

    first_name = request.form["first_name"]
    last_name = request.form["last_name"]
    email = request.form["email"]
    address = request.form["address"]
    zipcode = request.form["zipcode"]
    if 'admin' in request.form:
        admin = True
    else:
        admin = False
    password = request.form["password"]
    new_user = User(first_name=first_name, last_name=last_name, email=email, street_address=address, zipcode=zipcode,
                    admin=admin)
    new_user.hash_password(password)
    db.session.add(new_user)
    db.session.commit()
    flash("User {} added".format(email), 'info')
    return redirect("/users")


@app.route("/delete_user", methods=["POST"])
@login_required
@admin_required
def delete_user():
    """ Delete a user from the database """

    user_id = request.form['user_id']
    email = request.form['email']
    user = User.query.filter_by(user_id=user_id, email=email).first()
    db.session.delete(user)
    db.session.commit()
    flash("User {} deleted".format(email), 'info')
    return redirect("/users")


############################################################################
# Select a genre and input address for food

@app.route("/step_2", methods=["GET"])
@login_required
def choose_genre():
    """ User chooses genre """
    # User chooses a genre from the dropdown.

    return render_template("step_2_genre_and_food.html")


############################################################################
# Let Netflix and Chow make a food and movie choice

@app.route("/step_3", methods=["POST"])
@login_required
def get_choices_a():
    """ Submitting address for food delivery """
    session['address_choice'] = request.form['address']
    session['zipcode_choice'] = request.form['zipcode']
    session['movie_source'] = request.form['selection']
    print "Movie source: {}".format(session['movie_source'])
    return render_template("step_3_order_food.html")


@app.route("/get_choices")
@login_required
def get_choices_b():
    ###################
    # Food
    # Talk to Delivery.com and get all restaurants in general vicinity
    restaurant_results = talk_to_delivery_api(session['address_choice'], session['zipcode_choice'])
    # From the restaurants returned that are within the general vicinity, pick a random one
    my_restaurant_dict = pick_random_restaurant(restaurant_results)

    # A random restaurant has been chosen. This shows us what the choice is
    restaurant_name = my_restaurant_dict['name']
    restaurant_url = my_restaurant_dict['url']

    ###################
    # Lets pick a movie
    # First, let's find the total number of titles in the category/source
    # API Documentation: https://api.guidebox.com/apidocs#movies
    url = "{}/{}/{}/{}/1/1/{}/web".format(GUIDEBOX_BASE_URL, GUIDEBOX_REGION, GUIDEBOX_API_KEY,
                                          GUIDEBOX_API_DIRECTORY, session['movie_source'])
    response = requests.get(url)
    response.close()
    response_dict = response.json()
    movie_count = int(response_dict['total_results'])

    # Maybe need to add a try/except here to help with errors.

    # Next, let's pick a random movie
    random_movie = choice(xrange(1, movie_count))
    url = "{}/{}/{}/{}/{}/1/{}/web".format(GUIDEBOX_BASE_URL, GUIDEBOX_REGION, GUIDEBOX_API_KEY,
                                           GUIDEBOX_API_DIRECTORY, random_movie, session['movie_source'])
    print "Guidebox API url: {}".format(url)
    response = requests.get(url)
    response_dict = response.json()

    # Extract the movie data. [0] is the index of the movie as it returns only 1
    movie_title = response_dict["results"][0]["title"].decode('utf-8')
    movie_rating = response_dict["results"][0]["rating"]
    movie_release_year = response_dict["results"][0]["release_year"]
    movie_imdb = response_dict["results"][0]["imdb"]
    movie_id = response_dict["results"][0]["id"]
    if "default_movie_240x342.jpg" in response_dict["results"][0]["poster_240x342"]:
        movie_poster = "/static/img/rsz_cats_eating.png"
    else:
        movie_poster = response_dict["results"][0]["poster_240x342"]

    # Get playback information for movie
    url = "{}/{}/{}/movie/{}".format(GUIDEBOX_BASE_URL, GUIDEBOX_REGION, GUIDEBOX_API_KEY, movie_id)
    print "Guidebox URL for \"{}\": {}".format(movie_title, url)
    response = requests.get(url)
    response_dict = response.json()
    # This will return a random movie from the chosen source
    if session['movie_source'] == "xfinity":
        movie_service = response_dict["free_web_sources"][0]["display_name"]
        movie_playback_url = response_dict["free_web_sources"][0]["link"]
    if session['movie_source'] == "disney_movies_anywhere":
        movie_service = response_dict["purchase_web_sources"][0]["display_name"]
        movie_playback_url = response_dict["purchase_web_sources"][0]["link"]
    if session['movie_source'] == "hulu_free":
        movie_service = response_dict["free_web_sources"][0]["display_name"]
        movie_playback_url = response_dict["free_web_sources"][0]["link"]
    # This will return a random movie from the Showtime subscription source
    if session['movie_source'] == "showtime":
        movie_service = response_dict["subscription_web_sources"][0]["display_name"]
        movie_playback_url = response_dict["subscription_web_sources"][0]["link"]
    if session['movie_source'] == "hbo_now":
        movie_service = response_dict["subscription_web_sources"][0]["display_name"]
        movie_playback_url = response_dict["subscription_web_sources"][0]["link"]
    if session['movie_source'] == "itunes":
        movie_service = response_dict["purchase_web_sources"][0]["display_name"]
        movie_playback_url = response_dict["purchase_web_sources"][0]["link"]

    # https://api-public.guidebox.com/v1.43/US/rKiNl7heGsSWWC9yN04AaIOWhkHWuP3f/movies/all/1915/1/hulu_free/web

    # End the try/except here
    data = dict(restaurant_name=restaurant_name, restaurant_url=restaurant_url, movie_title=movie_title,
                movie_rating=movie_rating, movie_release_year=movie_release_year, movie_poster=movie_poster,
                movie_playback_url=movie_playback_url, movie_service=movie_service)
    audit_event(event="Random Choice - Restaurant: {}, Movie: {}".format(restaurant_name, movie_title))
    return jsonify(data)


@app.route('/step_4', methods=["POST"])
@login_required
def get_movie_choice():
    """ Submitting genre choice """
    # After user submits genre choice, a movie is randomly chosen for them.
    return render_template("unused_get_movie.html")


############################################################################
# Delivery.com API helper functions

def talk_to_delivery_api(address, zipcode):
    """This function will make the request to delivery.com's API, and return the
    result(s)"""

    # This is the URL for the API endpoint at delivery.com
    url = DELIVERY_BASE_API_URL + DELIVERY_ENDPOINT

    # Create a dict that contains the parameters we want to send to the deliver.com's API
    params = {'client_id': DELIVERY_API_KEY,
              'address': "{}, {}".format(address, zipcode),
              'method': DEFAULT_METHOD,
              'merchant_type': DEFAULT_MERCHANT_TYPE}

    # The requests library has a 'get' function to make the request. We send it the URL and params
    response = requests.get(url, params=params)  # This makes the request to the deliver.com API
    results_dict = response.json()
    # Close/end the network connection to delivery.com's API
    response.close()

    return results_dict


def pick_random_restaurant(restaurant_results):
    """ A random restaurant has been chosen. This shows us what the choice is """

    # I need to take the results, filter out all the restaurants and give the user
    # a randomly chosen restaurant.
    random_choice = choice(restaurant_results['merchants'])
    restaurant_name = random_choice['summary']['name']
    restaurant_url = random_choice['summary']['url']['complete']
    print 'Delivery.com choice: Name: {name}, URL: {url}'.format(name=restaurant_name, url=restaurant_url)
    return {'name': restaurant_name, 'url': restaurant_url}


############################################################################
# Auditing

def audit_event(user_id=None, event=None):
    """ Function to write audit events into database table named 'audit' """

    if not user_id:
        if 'user_id' in session:
            user_id = session['user_id']
        else:
            user_id = 0  # User number has to exist...could cretae a user with id=0 for auditing
    utc_timestamp = datetime.utcnow()

    # Heroku doesn't easily give the IP address of the client. However, the client IP address
    # can be found as the last item in the X-Forwarded-For list. Found on Stack Overflow.
    provided_ips = request.headers.getlist("X-Forwarded-For")
    if provided_ips:
        ip_address = provided_ips[-1]
    else:
        ip_address = request.remote_addr

    entry = Audit(timestamp=utc_timestamp, user_id=user_id, ip=ip_address,
                  user_agent=request.headers.get('User-Agent'), event=event)
    db.session.add(entry)
    db.session.commit()


############################################################################
# Error Pages

@app.errorhandler(404)
def page_not_found(error):
    """404 Page Not Found handling"""

    return render_template('/errors/404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    # db.session.rollback()
    """500 Error handling """

    return render_template('/errors/500.html'), 500

############################################################################
# Main routine

def main():
    # We have to set debug=True here, since it has to be True at the point
    # that we invoke the DebugToolbarExtension
    # app.debug = False

    # Raise error if Jinja encounters a problem
    app.jinja_env.undefined = StrictUndefined

    # Connect to the database
    connect_to_db(app)

    # Use the DebugToolbar
    DebugToolbarExtension(app)

    # Start the webserver
    port = int(os.environ.get("PORT", 5000))
    debug = 'ALLOW_DEBUG' not in os.environ
    app.run(debug=debug, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
