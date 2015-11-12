import requests  # This is required to talk to the API; make requests and get responses back
from random import choice  # This is so we can pick a random restaurant
import os

appkey = os.environ["DELIVERY_ACCESS_TOKEN_KEY"]

# Configuration for API (global variables ... naming them using all caps)
BASE_API_URL = 'https://api.delivery.com'  # Production Environment
DELIVERY_ENDPOINT = '/merchant/search/delivery'
DEFAULT_SEARCH_TERM = '683 Sutter St, 94102'
DEFAULT_METHOD = 'delivery'
DEFAULT_MERCHANT_TYPE = 'R'


##############################################################################
# Our functions


def talk_to_the_api(address):
    """This function will make the request to delivery.com's API, and return the
    result(s)"""

    # Below creates this: https://api.delivery.com/merchant/search/delivery?client_id=ODYzNzM4Mjg3NGI5YzUxNzdhOGQ4MzE0MmVlN2UzZmRl&address=100 Winchester Circle 95032

    # This is the URL for the API endpoint at delivery.com
    url = BASE_API_URL + DELIVERY_ENDPOINT

    # Create a dict that contains the parameters we want to send to the deliver.com's API
    params = {'client_id': appkey,
              'address': address,
              'method': DEFAULT_METHOD,
              'merchant_type': DEFAULT_MERCHANT_TYPE}

    # The requests library has a 'get' function to make the request. We send it the URL and params
    response = requests.get(url, params=params)  # This makes the request to the deliver.com API
    results = response.json()
    # Close/end the network connection to delivery.com's API
    response.close()

    return results


def pick_random_restaurant(restaurant_results):
    """ A random restaurant has been chosen. This shows us what the choice is """

    # I need to take the results, filter out all the restaurants and give the user
    # a randomly chosen restaurant.
    restaurant_url = my_restaurant['url']
    restaurant_name = my_restaurant['name']
    print 'name: {name}, url: {url}'.format(name=restaurant_name, url=restaurant_url)


def main():
    """
    This function, "main", performs the main logic of the this script
    """

    # Talk to Delivery.com and get all restaurants in general vicinit
    api_response = talk_to_the_api(address)

    # From the restaurants returned that match our cuisine type, and within the general
    # vicivnity, pick a random one
    my_restaurant = pick_random_restaurant(restaurant_results)

    # A random restaurant has been chosen. This shows us what the choice is
    restaurant_url = my_restaurant['url']
    restaurant_name = my_restaurant['name']
    print 'name: {name}, url: {url}'.format(name=restaurant_name, url=restaurant_url)




# if __name__ == "__main__":
#     main()
