# coding=utf-8


"""
This file purely defines the schema used in my database.
"""


# Things I needed to pip install
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


# Connection to our database
db = SQLAlchemy()


##############################################################################
# Model definitions

class User(db.Model):
    """User of Netflix and Chow site"""

    __tablename__ = "users"

    user_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    email = db.Column(db.String(64), nullable=False)
    password = db.Column(db.String(128), nullable=False)
    street_address = db.Column(db.Text, nullable=False)
    zipcode = db.Column(db.Integer, nullable=False)
    first_name = db.Column(db.Text, nullable=False)
    last_name = db.Column(db.Text, nullable=False)

    def __repr__(self):
        """Provide helpful representation when printed."""
        return "<User user_id={} email={}>".format(self.user_id, self.email)

    def hash_password(self, password):
        """Used for setting a hashed+salted password"""

        self.password = generate_password_hash(password)

    def verify_password(self, password):

        """Used to validate that passwods match
        :param password:
        :return:"""

        return check_password_hash(self.password, password)


class Audit(db.Model):
    """This is the audit log"""

    __tablename__ = "auditing"

    event_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    ip = db.Column(db.Text, nullable=False)
    user_agent = db.Column(db.Text, nullable=False)
    event = db.Column(db.Text, nullable=False)

    def __repr__(self):
        """
        Provide helpful representation when printed.
        """

        return "<event_id={} User user_id={} event={}>".format(self.event_id,
                                                               self.user_id,
                                                               self.email)


##############################################################################
# Helper functions


def connect_to_db(app):
    """Connect the database to our Flask app."""

    # Configure to use our SQLite database. Enter sqlite3 netflixandchow.db
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///netflixandchow.db'
    db.app = app
    db.init_app(app)

if __name__ == "__main__":
    # As a convenience, if we run this module interactively, it will leave
    # you in a state of being able to work with the database directly.

    from server import app
    connect_to_db(app)
    print "Connected to DB."
