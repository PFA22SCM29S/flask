'''
Goal of Flask Microservice:
1. Flask will take the repository_name such as angular, angular-cli, material-design, D3 from the body of the api sent from React app and 
   will utilize the GitHub API to fetch the created and closed issues. Additionally, it will also fetch the author_name and other 
   information for the created and closed issues.
2. It will use group_by to group the data (created and closed issues) by month and will return the grouped data to client (i.e. React app).
3. It will then use the data obtained from the GitHub API (i.e Repository information from GitHub) and pass it as a input request in the 
   POST body to LSTM microservice to predict and forecast the data.
4. The response obtained from LSTM microservice is also return back to client (i.e. React app).

Use Python/GitHub API to retrieve Issues/Repos information of the past 1 year for the following repositories:
- https: // github.com/angular/angular
- https: // github.com/angular/material
- https: // github.com/angular/angular-cli
- https: // github.com/d3/d3
'''
# Import all the required packages 
import os
from flask import Flask, jsonify, request, make_response, Response
from flask_cors import CORS
import json
import dateutil.relativedelta
from dateutil import *
from datetime import date
import pandas as pd
import requests

# Initilize flask app
app = Flask(__name__)
# Handles CORS (cross-origin resource sharing)
CORS(app)

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

'''
API route path is  "/api/forecast"
This API will accept only POST request
'''
@app.route('/api/github', methods=['POST'])
def github():
    body = request.get_json()
    # Extract the choosen repositories from the request
    repo_name = body['repository']
    # Add your own GitHub Token to run it local
    token = os.environ.get('GITHUB_TOKEN', 'YOUR_GITHUB_TOKEN')
    #token = os.environ.get('GITHUB_TOKEN', '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')
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

    issues_reponse = []
    # Iterating to get issues for every month for the past 24 months
    for i in range(24):
        last_month = today + dateutil.relativedelta.relativedelta(months=-1)
        types = 'type:issue'
        repo = 'repo:' + repo_name
        ranges = 'created:' + str(last_month) + '..' + str(today)
        # By default GitHub API returns only 30 results per page
        # The maximum number of results per page is 100
        # For more info, visit https://docs.github.com/en/rest/reference/repos 
        per_page = 'per_page=100'
        # Search query will create a query to fetch data for a given repository in a given time range
        search_query = types + ' ' + repo + ' ' + ranges

        # Append the search query to the GitHub API URL 
        query_url = GITHUB_URL + "search/issues?q=" + search_query + "&" + per_page
        # requsets.get will fetch requested query_url from the GitHub API
        search_issues = requests.get(query_url, headers=headers, params=params)
        # Convert the data obtained from GitHub API to JSON format
        search_issues = search_issues.json()
        issues_items = []
        try:
            # Extract "items" from search issues
            issues_items = search_issues.get("items")
        except KeyError:
            error = {"error": "Data Not Available"}
            resp = Response(json.dumps(error), mimetype='application/json')
            resp.status_code = 500
            return resp
        if issues_items is None:
            continue
        for issue in issues_items:
            label_name = []
            data = {}
            current_issue = issue
            # Get issue number
            data['issue_number'] = current_issue["number"]
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
            issues_reponse.append(data)

        today = last_month

    df = pd.DataFrame(issues_reponse)

    # Daily Created Issues
    df_created_at = df.groupby(['created_at'], as_index=False).count()
    dataFrameCreated = df_created_at[['created_at', 'issue_number']]
    dataFrameCreated.columns = ['date', 'count']

    '''
    Monthly Created Issues
    Format the data by grouping the data by month
    ''' 
    created_at = df['created_at']
    month_issue_created = pd.to_datetime(
        pd.Series(created_at), format='%Y/%m/%d')
    month_issue_created.index = month_issue_created.dt.to_period('m')
    month_issue_created = month_issue_created.groupby(level=0).size()
    month_issue_created = month_issue_created.reindex(pd.period_range(
        month_issue_created.index.min(), month_issue_created.index.max(), freq='m'), fill_value=0)
    month_issue_created_dict = month_issue_created.to_dict()
    created_at_issues = []
    for key in month_issue_created_dict.keys():
        array = [str(key), month_issue_created_dict[key]]
        created_at_issues.append(array)

    '''
    Monthly Closed Issues
    Format the data by grouping the data by month
    ''' 
    
    closed_at = df['closed_at'].sort_values(ascending=True)
    month_issue_closed = pd.to_datetime(
        pd.Series(closed_at), format='%Y/%m/%d')
    month_issue_closed.index = month_issue_closed.dt.to_period('m')
    month_issue_closed = month_issue_closed.groupby(level=0).size()
    month_issue_closed = month_issue_closed.reindex(pd.period_range(
        month_issue_closed.index.min(), month_issue_closed.index.max(), freq='m'), fill_value=0)
    month_issue_closed_dict = month_issue_closed.to_dict()
    closed_at_issues = []
    for key in month_issue_closed_dict.keys():
        array = [str(key), month_issue_closed_dict[key]]
        closed_at_issues.append(array)


    '''
    Weekly created closed issues 52*2=104 weeks    
    '''
    today1 = date.today()

    issues_reponse1 = []
    # Iterating to get issues for every month for the past 24 months
    for i in range(104):
        last_week = today1 + dateutil.relativedelta.relativedelta(days=-7)
        types = 'type:issue'
        repo = 'repo:' + repo_name
        ranges = 'created:' + str(last_week) + '..' + str(today1)
        # By default GitHub API returns only 30 results per page
        # The maximum number of results per page is 100
        # For more info, visit https://docs.github.com/en/rest/reference/repos 
        per_page = 'per_page=100'
        # Search query will create a query to fetch data for a given repository in a given time range
        search_query = types + ' ' + repo + ' ' + ranges

        # Append the search query to the GitHub API URL 
        query_url = GITHUB_URL + "search/issues?q=" + search_query + "&" + per_page
        # requsets.get will fetch requested query_url from the GitHub API
        search_issues = requests.get(query_url, headers=headers, params=params)
        # Convert the data obtained from GitHub API to JSON format
        search_issues = search_issues.json()
        issues_items = []
        try:
            # Extract "items" from search issues
            issues_items = search_issues.get("items")
        except KeyError:
            error = {"error": "Data Not Available"}
            resp = Response(json.dumps(error), mimetype='application/json')
            resp.status_code = 500
            return resp
        if issues_items is None:
            continue
        for issue in issues_items:
            label_name = []
            data = {}
            current_issue = issue
            # Get issue number
            data['issue_number'] = current_issue["number"]
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
            issues_reponse1.append(data)

        today1 = last_week

    df1 = pd.DataFrame(issues_reponse1)

    '''
    Weekly Closed Issues
    Format the data by grouping the data by month
    ''' 
    
    closed_at = df1['closed_at'].sort_values(ascending=True)
    week_issue_closed = pd.to_datetime(
        pd.Series(closed_at), format='%Y/%m/%d')
    week_issue_closed.index = week_issue_closed.dt.to_period('d')
    week_issue_closed = week_issue_closed.groupby(level=0).size()
    week_issue_closed = week_issue_closed.reindex(pd.period_range(
        week_issue_closed.index.min(), week_issue_closed.index.max(), freq='d'), fill_value=0)
    week_issue_closed_dict = week_issue_closed.to_dict()
    closed_at_issues1 = []
    for key in week_issue_closed_dict.keys():
        array = [str(key), week_issue_closed_dict[key]]
        closed_at_issues1.append(array)


    '''
    Pull request code
    '''
    pull_reponse = []
    # Iterating to get issues for every month for the past 24 months
    for i in range(24):
        last_month = today + dateutil.relativedelta.relativedelta(months=-1)
        types = 'type:pulls'
        repo = repo_name
        ranges = 'created:' + str(last_month) + '..' + str(today)
        # By default GitHub API returns only 30 results per page
        # The maximum number of results per page is 100
        # For more info, visit https://docs.github.com/en/rest/reference/repos 
        per_page = 'per_page=100'
        # Search query will create a query to fetch data for a given repository in a given time range
        # Search query will create a query to fetch data for a given repository in a given time range
        search_query = types  + ' ' + ranges

        # Append the search query to the GitHub API URL 
        query_url = GITHUB_URL +'repos/' + repo + "/pulls?q=" + search_query + "&" + per_page 
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
            data['issue_number'] = current_issue["number"]
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
    

    '''
    Commits
    '''
    commit_reponse = []
    # Iterating to get issues for every month for the past 24 months
    for i in range(24):
        last_month = today + dateutil.relativedelta.relativedelta(months=-1)
        types = 'type:commits'
        repo = repo_name
        ranges = 'created:' + str(last_month) + '..' + str(today)
        # By default GitHub API returns only 30 results per page
        # The maximum number of results per page is 100
        # For more info, visit https://docs.github.com/en/rest/reference/repos 
        per_page = 'per_page=100'
        # Search query will create a query to fetch data for a given repository in a given time range
        # Search query will create a query to fetch data for a given repository in a given time range
        search_query = types  + ' ' + ranges

        # Append the search query to the GitHub API URL 
        query_url = GITHUB_URL +'repos/' + repo + "/commits?q=" + search_query + "&" + per_page 
        # requsets.get will fetch requested query_url from the GitHub API
        query_url = GITHUB_URL +'repos/' + repo + "/pulls?q=" + search_query + "&" + per_page 
        search_issues = requests.get(query_url, headers=headers, params=params)
        # Convert the data obtained from GitHub API to JSON format
        search_issues = search_issues.json()
        commit_items = []
        try:
            # Extract "items" from search issues
            commit_items = search_issues
        except KeyError:
            error = {"error": "Data Not Available"}
            resp = Response(json.dumps(error), mimetype='application/json')
            resp.status_code = 500
            return resp
        if commit_items is None:
            continue
        for pulls in commit_items:
            label_name = []
            data = {}
            current_issue = pulls
            # Get issue number
            data['issue_number'] = current_issue["number"]
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
            commit_reponse.append(data)

        today = last_month

    '''
    Branches
    '''
    branch_reponse = []
    # Iterating to get issues for every month for the past 24 months
    for i in range(24):
        last_month = today + dateutil.relativedelta.relativedelta(months=-1)
        types = 'type:commits'
        repo = repo_name
        ranges = 'created:' + str(last_month) + '..' + str(today)
        # By default GitHub API returns only 30 results per page
        # The maximum number of results per page is 100
        # For more info, visit https://docs.github.com/en/rest/reference/repos 
        per_page = 'per_page=100'
        # Search query will create a query to fetch data for a given repository in a given time range
        # Search query will create a query to fetch data for a given repository in a given time range
        search_query = types  + ' ' + ranges

        # Append the search query to the GitHub API URL 
        query_url = GITHUB_URL +'repos/' + repo + "/branches?q=" + search_query + "&" + per_page 
        # requsets.get will fetch requested query_url from the GitHub API
        query_url = GITHUB_URL +'repos/' + repo + "/pulls?q=" + search_query + "&" + per_page                
        search_issues = requests.get(query_url, headers=headers, params=params)
        # Convert the data obtained from GitHub API to JSON format
        search_issues = search_issues.json()
        commit_items = []
        try:
            # Extract "items" from search issues
            commit_items = search_issues
        except KeyError:
            error = {"error": "Data Not Available"}
            resp = Response(json.dumps(error), mimetype='application/json')
            resp.status_code = 500
            return resp
        if commit_items is None:
            continue
        for pulls in commit_items:
            label_name = []
            data = {}
            current_issue = pulls
            # Get issue number
            data['issue_number'] = current_issue["number"]
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
            branch_reponse.append(data)

        today = last_month


    '''
    Contributors
    '''
    contri_reponse = []
    # Iterating to get issues for every month for the past 24 months
    for i in range(24):
        last_month = today + dateutil.relativedelta.relativedelta(months=-1)
        types = 'type:contributor'
        repo = repo_name
        ranges = 'created:' + str(last_month) + '..' + str(today)
        # By default GitHub API returns only 30 results per page
        # The maximum number of results per page is 100
        # For more info, visit https://docs.github.com/en/rest/reference/repos 
        per_page = 'per_page=100'
        # Search query will create a query to fetch data for a given repository in a given time range
        # Search query will create a query to fetch data for a given repository in a given time range
        search_query = types  + ' ' + ranges

        # Append the search query to the GitHub API URL 
        query_url = GITHUB_URL +'repos/' + repo + "/contributor?q=" + search_query + "&" + per_page 
               # requsets.get will fetch requested query_url from the GitHub API
        query_url = GITHUB_URL +'repos/' + repo + "/pulls?q=" + search_query + "&" + per_page                
        search_issues = requests.get(query_url, headers=headers, params=params)
        # Convert the data obtained from GitHub API to JSON format
        search_issues = search_issues.json()
        commit_items = []
        try:
            # Extract "items" from search issues
            commit_items = search_issues
        except KeyError:
            error = {"error": "Data Not Available"}
            resp = Response(json.dumps(error), mimetype='application/json')
            resp.status_code = 500
            return resp
        if commit_items is None:
            continue
        for pulls in commit_items:
            label_name = []
            data = {}
            current_issue = pulls
            # Get issue number
            data['issue_number'] = current_issue["number"]
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
            contri_reponse.append(data)

        today = last_month

    '''
    Releases
    '''

    '''
        1. Hit LSTM Microservice by passing issues_response as body
        2. LSTM Microservice will give a list of string containing image paths hosted on google cloud storage
        3. On recieving a valid response from LSTM Microservice, append the above json_response with the response from
            LSTM microservice
    '''
    created_at_body = {
        "issues": issues_reponse,
        "type": "created_at",
        "repo": repo_name.split("/")[1]
    }
    closed_at_body = {
        "issues": issues_reponse,
        "type": "closed_at",
        "repo": repo_name.split("/")[1]
    }
    pulls_at_body = {
        "issues": issues_reponse,
        "type": "created_at",
        "repo": repo_name.split("/")[1]
    }
    commit_at_body = {
        "issues": issues_reponse,
        "type": "closed_at",
        "repo": repo_name.split("/")[1]
    }    
    branches_at_body = {
        "issues": issues_reponse,
        "type": "created_at",
        "repo": repo_name.split("/")[1]
    }        
    contributor_at_body = {
        "issues": issues_reponse,
        "type": "closed_at",
        "repo": repo_name.split("/")[1]
    } 
    releases_at_body = {
        "issues": issues_reponse,
        "type": "created_at",
        "repo": repo_name.split("/")[1]
    }           

    # Update your Google cloud deployed LSTM app URL (NOTE: DO NOT REMOVE "/")
    LSTM_API_URL = "https://lstm-dijoq5joua-uc.a.run.app/" + "api/forecast"
    #LSTM_API_URL = "http://10.0.0.178:8080/"+ "api/forecast"
    '''
    Trigger the LSTM microservice to forecasted the created issues
    The request body consists of created issues obtained from GitHub API in JSON format
    The response body consists of Google cloud storage path of the images generated by LSTM microservice
    '''
    created_at_response = requests.post(LSTM_API_URL,
                                        json=created_at_body,
                                        headers={'content-type': 'application/json'})
    
    '''
    Trigger the LSTM microservice to forecasted the closed issues
    The request body consists of closed issues obtained from GitHub API in JSON format
    The response body consists of Google cloud storage path of the images generated by LSTM microservice
    '''    
    closed_at_response = requests.post(LSTM_API_URL,
                                       json=closed_at_body,
                                       headers={'content-type': 'application/json'})
    
    pulls_response = requests.post(LSTM_API_URL,
                                       json=pulls_at_body,
                                       headers={'content-type': 'application/json'})

    commits_response = requests.post(LSTM_API_URL,
                                       json=commit_at_body,
                                       headers={'content-type': 'application/json'})
    branches_response = requests.post(LSTM_API_URL,
                                       json=branches_at_body,
                                       headers={'content-type': 'application/json'})
    contributors_response = requests.post(LSTM_API_URL,
                                       json=contributor_at_body,
                                       headers={'content-type': 'application/json'}) 
    releases_response = requests.post(LSTM_API_URL,
                                       json=releases_at_body,
                                       headers={'content-type': 'application/json'})                                                                                                                    
    '''
    Create the final response that consists of:
        1. GitHub repository data obtained from GitHub API
        2. Google cloud image urls of created and closed issues obtained from LSTM microservice
    '''
    json_response = {
        "created": created_at_issues,
        "closed": closed_at_issues,
        "closed_week": closed_at_issues1,
        "starCount": ["count",repository["stargazers_count"]],
        "forkCount": ["count",repository["forks_count"]],
        "stacked": [{"name":"created", "data":created_at_issues},{"name":"closed","data":closed_at_issues}],
        "max_issue_created_day": max(created_at_issues,key=lambda x:x[1]),
        "max_issue_closed_day":max(closed_at_issues1,key=lambda x:x[1]),
        "max_issue_close_month":max(closed_at_issues1,key=lambda x:x[1])[0][5:7],
        "createdAtImageUrls": {
            **created_at_response.json(),
        },
        "closedAtImageUrls": {
            **closed_at_response.json(),
        },
        "PullsImageUrls": {
            **pulls_response.json(),
        },
        "CommitsImageUrls": {
            **commits_response.json(),
        },
        "BranchesImageUrls": {
            **branches_response.json(),
        }, 
        "ContributorsImageUrls": {
            **contributors_response.json(),
        }, 
        "ReleasesImageUrls": {
            **releases_response.json(),
        },                              
    }
    print("json ",json_response)
    # Return the response back to client (React app)
    return jsonify(json_response)


# Run flask app server on port 5000
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
