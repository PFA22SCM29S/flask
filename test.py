from flask import Flask, jsonify, request, make_response, Response
import json,os
import dateutil.relativedelta
from dateutil import *
from datetime import date
import pandas as pd
import requests

# Add response headers to accept all types of  requests
def build_preflight_response():
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type")
    response.headers.add("Access-Control-Allow-Methods",
                         "PUT, GET, POST, DELETE, OPTIONS")
    return response

# Modify response headers when returning to the origin
def build_actual_response(response):
    response.headers.set("Access-Control-Allow-Origin", "*")
    response.headers.set("Access-Control-Allow-Methods",
                         "PUT, GET, POST, DELETE, OPTIONS")
    return response

def main():

    repo_name ='angular/angular'

    token = os.environ.get('GITHUB_TOKEN', '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')
    GITHUB_URL = f"https://api.github.com/"
    headers = {
        "Authorization": f'token {token}'
    }
    params = {
        "state": "open"
    }
    repository_url = GITHUB_URL + "repos/" + repo_name
    # Fetch GitHub data from GitHub API
    repository = requests.get(repository_url, headers=headers)
    # Convert the data obtained from GitHub API to JSON format
    repository = repository.json()
    today = date.today()
    pull_reponse = []
    # Iterating to get issues for every month for the past 24 months
    for i in range(24):
        last_month = today + dateutil.relativedelta.relativedelta(months=-1)
        types = 'type:pull'
        repo = repo_name
        ranges = 'created:' + str(last_month) + '..' + str(today)
        # By default GitHub API returns only 30 results per page
        # The maximum number of results per page is 100
        # For more info, visit https://docs.github.com/en/rest/reference/repos 
        per_page = 'per_page=100'

        # Search query will create a query to fetch data for a given repository in a given time range
        search_query = types  + ' ' + ranges

        # Append the search query to the GitHub API URL 
        query_url = GITHUB_URL +'repos/' + repo + "/pulls?q=" + search_query + "&" + per_page
        print(query_url)
        exit(0)
        # requsets.get will fetch requested query_url from the GitHub API
        search_issues = requests.get(query_url, headers=headers, params=params)
        # Convert the data obtained from GitHub API to JSON format
        search_issues = search_issues.json()
        pulls_items = []
        try:
            # Extract "items" from search issues
            pulls_items = search_issues
        except KeyError:
            error = {"error": "Data Not Available"}
            resp = Response(json.dumps(error), mimetype='application/json')
            resp.status_code = 500
            return resp
        if pulls_items is None:
            continue
        for pulls in pulls_items:
            label_name = []
            data = {}
            current_issue = pulls
            # Get issue number
            data['pull_number'] = current_issue["number"]
            # Get created date of issue
            data['created_at'] = current_issue["created_at"][0:10]
            if current_issue["closed_at"] == None:
                data['closed_at'] = current_issue["closed_at"]
            else:
                # Get closed date of issue
                data['closed_at'] = current_issue["closed_at"][0:10]
            for label in current_issue["labels"]:
                # Get label name of issue
                label_name.append(label["name"])
            data['labels'] = label_name
            # It gives state of issue like closed or open
            data['State'] = current_issue["state"]
            # Get Author of issue
            data['Author'] = current_issue["user"]["login"]
            pull_reponse.append(data)

        today = last_month

main()