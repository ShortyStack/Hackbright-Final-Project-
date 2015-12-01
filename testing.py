""" Test suite for Netflix and Chow """

import os
import unittest
from server import app
from model import db, connect_to_db, User, Audit

# Not sure I am needed these, but I put them in just in case
# DELIVERY_API_KEY = os.environ["DELIVERY_ACCESS_TOKEN_KEY"]
# GUIDEBOX_API_KEY = os.environ["GUIDEBOX_API_KEY"]


class FlaskTestCase(unittest.TestCase):
    """Tests for Netflix and Chow app for functions that don't require sessions."""

    def setup(self):
        # set up fake test browser
        self.client = app.test_client()

        # Connect to the database
        connect_to_db(app)

        # This line makes a 500 error in a route raise an error in a test
        app.config['TESTING'] = True


    #############################################################################
    # Test standard template pages

    def test_load_homepage(self):
        """Tests to see if the index page comes up."""
        self.client = app.test_client()
        result = self.client.get('/')
        self.assertEqual(result.status_code, 200)
        self.assertIn('Sit back, relax and let us plan your evening.', result.data)

    def test_404(self):
        """Tests to see if requesting a non-existent page returns a custom 404"""
        self.client = app.test_client()
        result = self.client.get('/foobar')
        self.assertEqual(result.status_code, 404)
        self.assertIn('This is not the page you are looking for.', result.data)


    #############################################################################
    # Test authentication

    def test_process_signup_known_user(self):
        """Test a valid login"""
        self.client = app.test_client()
        #  app.config['TESTING'] = True  # Commented out because NULL IP trying to be written to audit log
        connect_to_db(app)
        result = self.client.post('/login-process',
                                  data={'email': "billy@testuser.com",
                                        'password': "Testing123!"},
                                  follow_redirects=True)


if __name__ == "__main__":
    unittest.main()
