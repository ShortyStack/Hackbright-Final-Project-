""" Test suite for Netflix and Chow """

import os
import unittest
from server import app
from model import db, connect_to_db, User, Audit

# Not sure I am needed these, but I put them in just in case
DELIVERY_API_KEY = os.environ["DELIVERY_ACCESS_TOKEN_KEY"]
GUIDEBOX_API_KEY = os.environ["GUIDEBOX_API_KEY"]


class flaskTest(unittest, TestCase):
    """Tests for Netflix and Chow app for functions that don't require sessions."""

    def setUp(self):
        # set up fake test browser
        self.client = app.test_client()

    def test_load_homepage(self):
        """Tests to see if the index page comes up."""
        result = self.client.get('/')

        self.assertEqual(result.status_code, 200)

    def test_load_login(self):
        """Tests to see if the login page comes up."""

        result = self.client.get('/login')


def tearDown(self):
    pass


if __name__ ==“__main__”:
    unitest.main()