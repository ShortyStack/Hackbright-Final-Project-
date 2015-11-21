"""Utility file to seed ratings database from MovieLens data in seed_data/"""
# seed.py populates the tables.

from model import User
# from model import Audit
from model import connect_to_db, db
from server import app

from datetime import datetime


def load_users():
    """Load users from user.csv into database."""
    # open file
    user_csv = open("user.csv")
    # Iterate through the lines
    # This will put the data into a list
    for line in user_csv:
        line_list = line.strip().split("|")
        # Another for loop to iterate through
        for i in range(len(line_list)):
            line_list[i] = line_list[i].strip()
        user_id, email, password, street_address, zipcode, first_name, last_name, admin = line_list[0], line_list[1], \
                                                                                          line_list[2], line_list[3], \
                                                                                          line_list[4], line_list[5], \
                                                                                          line_list[6], line_list[7]

        print "EMAIL: {}, PASSWORD: {}, STREET_ADDRESS: {}, ZIPCODE: {}, FIRST {}, LAST {}".format(email, password,
                                                                                                   street_address,
                                                                                                   zipcode, first_name,
                                                                                                   last_name)

        user = User(user_id=user_id, email=email, street_address=street_address, zipcode=zipcode, first_name=first_name,
                    last_name=last_name, admin=admin)
        user.hash_password(password)

        db.session.add(user)
    db.session.commit()


if __name__ == "__main__":
    connect_to_db(app)

    # In case tables haven't been created, create them
    db.create_all()

    # Import different types of data
    load_users()
