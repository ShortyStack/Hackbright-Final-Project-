# coding=utf-8
#
# TODO:
# 1. Add more robust error handling (talk to API and web server is down........)  *
# 2. Add admin page (add users, delete users, view audit logs)
# 4. Add modal windows for movie and food execution  ***
# 5. Use Ajax to display loading animated gif while talking to API's  *
# 6. Add geolocation for users food delivery address screen  **
# 7. Deploy to [Heroku] server  *
# 8. What do I need to do specifically for the admin information (@app.route ("/login_process")
#
# ChangeLog:
# + Got basic MVP working (2015-11-15)
# + Replaced genre section to movie source section. (This is in step_2)
# + Add non free sources (Amazon, HBO....)
# + Add event audit logs (user-agent, referrer, client IP address)


"""
Netflix and Chow
Written by: Wendy Zenone (2015-11-14)
"""


# Import local libraries
import os
from datetime import datetime
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
app.secret_key = "&\xd9\x9d\x14\x0b\xa7\xdc\xa1fJ;\xa2-\xff\xc9\x9fdh\xfc.\xa9\xdf\xc1\x99"


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
        print "Failed login attempt: {}:{}".format(email, password)  # DEBUG - Delete before go-live
        flash("Invalid login", "info")
        audit_event(event="Failed login attempt ({}:{})".format(email, password))
        return redirect("/login")


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
    admin = 0

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


############################################################################
# Administrative

@app.route("/admin", methods=["GET"])
@login_required
@admin_required
def manage_users_page():
    """ Manage users """

    users = User.query.all()
    audit_event(event="User accessed admin page")
    return render_template("/administrative/admin.html", users=users)


@app.route("/add_user", methods=["POST"])
@login_required
@admin_required
def add_user():
    """ Add user to db """

    first_name = request.form["first_name"]
    last_name = request.form["last_name"]
    email = request.form["email"]
    if 'admin' in request.form:
        admin = True
    else:
        admin = False
    password = request.form["password"]
    new_user = User(first_name=first_name, last_name=last_name, email=email, admin=admin)
    new_user.hash_password(password)
    db.session.add(new_user)
    db.session.commit()
    flash("User {} added".format(email), 'info')
    return redirect("/admin")


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
    return redirect("/admin")


@app.route("/audit_logs")
@login_required
@admin_required
def audit_logs():
    """ Audit Logs """

    return render_template("/audit.html")


@app.route("/get_audit_logs", methods=["POST"])
@login_required
@admin_required
def get_audit_logs(page=1, entries=5):
    """  Get the audit logs """

    # Logs = Audit.query.filter_by().all()
    if 'entries' in request.form:
        entries = int(request.form['entries'])
    else:
        entries = entries
    logs = Audit.query.filter_by().paginate(page=page, per_page=entries)
    data = {
        'config': dict(has_next=logs.has_next, has_prev=logs.has_prev, next_num=logs.next_num, prev_num=logs.prev_num),
        'data': {}}
    for i, log in enumerate(logs.items):
        data['data'][i] = dict(id=log.id, utc_timestamp=log.utc_timestamp, warn_level=log.warn_level,
                               user_id=log.user_id, event=log.event, ip=log.ip, user_agent=log.user_agent)
    return jsonify(data)


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

    # Below creates this: https://api.delivery.com/merchant/search/delivery?client_id=ODYzNzM4Mjg3NGI5YzUxNzdhOGQ4MzE0MmVlN2UzZmRl&address=100 Winchester Circle 95032

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
    entry = Audit(timestamp=utc_timestamp, user_id=user_id, ip=request.remote_addr,
                  user_agent=request.headers.get('User-Agent'), event=event)
    db.session.add(entry)
    db.session.commit()


############################################################################
# Main routine

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
