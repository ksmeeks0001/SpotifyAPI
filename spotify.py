import time
import logging
from enum import Enum

import requests


class UnauthorizedException(Exception):
    def __init__(self, url):
        super().__init__(f"Failed to retrieve auth token: {url}")


class RateLimitedException(Exception):
    def __init__(self, url):
        super().__init__(f"You are being rate limited, consider increasing wait time between failed requests: {url}")


class Search(Enum):
    ARTIST = 1
    PLAYLIST = 2
    TRACK = 3
    SHOW = 4
    EPISODE = 5


class Spotify:

    BASE_URL = "https://api.spotify.com/v1/"
    
    def __init__(self, client_id, client_secret, wait_time=30):
        self._client_id = client_id
        self._client_secret = client_secret
        self._wait_time = wait_time

        self._token = None

    def search(self, q, search_type=None, limit=None):           

        params = {"q": q}
        
        if search_type is not None:
            if type(search_type) != Search:
                raise Exception("Invalid Search Type Argument")
            params["type"] = search_type.name.lower()
            
        if limit is not None:
            params["limit"] = limit
            
        return self._get("search", params)


    def _get_token(self):

        logging.debug("Retrieving token")
        resp = requests.post(
            "https://accounts.spotify.com/api/token",
            data = {
                    "grant_type":"client_credentials",
                    "client_id":self._client_id,
                    "client_secret":self._client_secret
            })
        resp.raise_for_status()
        self._token = resp.json()['access_token']
        
                
    def _get(self, endpoint, params=None, retry=False):
        """
        Make a GET request to endpoint

        Will attempt to retrieve an authorization token if needed. If rate limit occurs, the request will retry.
        A retry or auth token retrieval will only occur once, otherwise an exception will be thrown. 
        
        """
        if self._token is None:
            self._get_token()
        url = self.BASE_URL + endpoint
        resp = requests.get(url, headers = {"Authorization": f"Bearer {self._token}"}, params=params)
        
        # If Unauthorized attempt to get new token
        if resp.status_code == 403 and retry == False:
            logging.debug("response was unauthorized retrying")
            self._token = None
            return self._get(endpoint, params, retry=True)
        elif resp.status_code == 403:
            raise UnauthorizedException(url)

        # if rate limited wait and try again
        if resp.status_code == 429 and retry == False:
            time.sleep(self._wait_time)
            return self._get(endpoint, params, retry=True)
        elif resp.status_code == 429:
            raise RateLimitedException(url)

        resp.raise_for_status()

        return resp.json()
    

