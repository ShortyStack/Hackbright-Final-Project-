# coding=utf-8
#
# TODO:
# 1. Handle error if no restaurants are returned
# 2. Add event audit logs (user-agent, referrer, client IP address)
# 3. Add admin page (add users, delete users, view audit logs)
# 4. Add non free sources (Amazon, HBO....)
# 5. Replace genre section to movie source section. (This is in step_2)
# 6. Add modal windows for movie and food execution
# 7. Use Ajax to display loading animated gif while talking to API's
# 8. Add more robust error handling (talk to API and web server is down........)
# 9. Add geolocation for users food delivery address screen
#
# ChangeLog:
# + Got basic MVP working (2015-11-15)
#


"""
Netflix and Chow
Written by: Wendy Zenone (2015-11-14)
"""


# Import libraries
import os
import requests
from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_debugtoolbar import DebugToolbarExtension
from functools import wraps
from jinja2 import StrictUndefined
from model import db, connect_to_db, User
from random import choice


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
GUIDEBOX_TOTAL_MOVIE_COUNT = 9482


# Create Flask object
app = Flask(__name__, static_folder='static')

# If you want to generate random key, go into Python and type:
# >>> import os
# >>> os.urandom(24)
app.secret_key = "&\xd9\x9d\x14\x0b\xa7\xdc\xa1fJ;\xa2-\xff\xc9\x9fdh\xfc.\xa9\xdf\xc1\x99"


############################################################################
# Make sure a user is logged in to access protected resources

def login_required(f):
    """
    This will require a user to be logged in to access a protected route
    """

    @wraps(f)
    def decorated_function():
        """
        The function that does the login enforcement
        """
        if not session.get('user_id'):
            return redirect(url_for('homepage'))
        return f()

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
        return redirect("/")
    else:
        print "Failed login attempt: {}:{}".format(email, password)  # DEBUG - Delete before go-live
        flash("Invalid login", "info")
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
    return redirect("/")


############################################################################
# Register

@app.route("/register", methods=["GET"])
def registration_form():
    """Display account creation page for the user"""

    return render_template("register.html")


@app.route("/register-process", methods=['POST'])
def register_process():
    """Add user to database. login_submit"""

    # inputs form the form checking the db to see if user is in DB already
    email = request.form['email']
    password = request.form['password']
    street_address = request.form['address']
    zipcode = request.form['zipcode']
    first_name = request.form['first_name']
    last_name = request.form['last_name']

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
                        last_name=last_name)
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
        return redirect("/")


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
def get_food_choice():
    """ Submitting address for food delivery """
    street_address = request.form['address']
    zipcode = request.form['zipcode']

    # Talk to Delivery.com and get all restaurants in general vicinity
    restaurant_results = talk_to_delivery_api(street_address, zipcode)

    # From the restaurants returned that are within the general vicinity, pick a random one
    my_restaurant_dict = pick_random_restaurant(restaurant_results)

    # A random restaurant has been chosen. This shows us what the choice is
    restaurant_name = my_restaurant_dict['name']
    restaurant_url = my_restaurant_dict['url']

    # Lets pick a movie
    random_movie = choice(xrange(1, GUIDEBOX_TOTAL_MOVIE_COUNT))
    url = "{}/{}/{}/{}/{}/1/free/all".format(GUIDEBOX_BASE_URL, GUIDEBOX_REGION, GUIDEBOX_API_KEY,
                                             GUIDEBOX_API_DIRECTORY, random_movie)
    print "Movie url: ".format(url)
    response = requests.get(url)
    response_dict = response.json()

    # Extract the movie data. [0] is the index of the movie as it returns only 1
    movie_title = response_dict["results"][0]["title"]
    movie_rating = response_dict["results"][0]["rating"]
    movie_release_year = response_dict["results"][0]["release_year"]
    movie_imdb = response_dict["results"][0]["imdb"]
    movie_id = response_dict["results"][0]["id"]
    movie_poster = response_dict["results"][0]["poster_240x342"]

    # Get playback information for movie
    url = "{}/{}/{}/movie/{}".format(GUIDEBOX_BASE_URL, GUIDEBOX_REGION, GUIDEBOX_API_KEY, movie_id)
    response = requests.get(url)
    response_dict = response.json()
    movie_playback_url = response_dict["free_web_sources"][0]["link"]
    movie_service = response_dict["free_web_sources"][0]["display_name"]

    return render_template("step_4_order_food.html", restaurant_name=restaurant_name, restaurant_url=restaurant_url,
                           movie_title=movie_title, movie_rating=movie_rating, movie_release_year=movie_release_year,
                           movie_poster=movie_poster, movie_playback_url=movie_playback_url,
                           movie_service=movie_service)


@app.route('/step_4', methods=["POST"])
@login_required
def get_movie_choice():
    """ Submitting genre choice """
    # After user submits genre choice, a movie is randomly chosen for them.
    return render_template("step_3_get_movie.html")


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
