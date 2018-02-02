# -*- coding: utf-8 -*-
"""
This sample demonstrates a simple skill built with the Amazon Alexa Skills Kit.
The Intent Schema, Custom Slots, and Sample Utterances for this skill, as well
as testing instructions are located at http://amzn.to/1LzFrj6

For additional samples, visit the Alexa Skills Kit Getting Started guide at
http://amzn.to/1LGWsLG

pip install requests -t . --upgrade
pip install configparser -t . --upgrade
pip install urllib3 -t . --upgrade
pip install simplejson -t . --upgrade

"""
from __future__ import print_function
import requests                 # need this for Get/Post/Delete
import simplejson as json       # need this for JSON
import configparser


# from requests.packages.urllib3.exceptions import InsecureRequestWarning


# We'll start with a couple of globals...
CardTitlePrefix = "VMC_DEMO"

config = configparser.ConfigParser()
config.read("./config.ini")
strProdURL      = config.get("vmcConfig", "strProdURL")
strCSPProdURL   = config.get("vmcConfig", "strCSPProdURL")
strAccessKey    = config.get("vmcConfig", "strAccessKey")
sddcID          = config.get("vmcConfig", "sddcID")
tenantID        = config.get("vmcConfig", "tenantID")
slackURL        = config.get("vmcConfig", "slackURL")

class data():
    sessiontoken    = ""
    sddc_name       = ""
    sddc_status     = ""
    sddc_region     = ""
    sddc_cluster    = ""
    sddc_hosts      = 0

slack_channel = False
sddc_list = []


def get_access_token(myKey):
    print('Getting access token with key: {}'.format(myKey))
    params = {'refresh_token': myKey}
    headers = {'Content-Type': 'application/json'}
    # update below ....
    response = requests.post('https://console.cloud.vmware.com/csp/gateway/am/api/auth/api-tokens/authorize',
                             params=params, headers=headers)
    json_response = response.json()
    access_token = json_response['access_token']
    return access_token


def get_sddc_data():
    data.sessiontoken = get_access_token(strAccessKey)
    myHeader = {'csp-auth-token': data.sessiontoken}
    myURL = strProdURL + "/vmc/api/orgs/" + tenantID + "/sddcs/" + sddcID
    response = requests.get(myURL, headers=myHeader)
    json_response = response.json()
    data.sddc_hosts     = 0
    data.sddc_name      = json_response['name']
    data.sddc_status    = json_response['sddc_state']
    data.sddc_cluster   = json_response['resource_config']['clusters'][0]['cluster_name']

    if (json_response['resource_config']['region']) == "US_WEST_2":
        data.sddc_region = "Oregon"
    else:
        data.sddc_region = "Virginia"
    if json_response['resource_config']:
        hosts = json_response['resource_config']['esx_hosts']
    if hosts:
        for j in hosts:
            data.sddc_hosts += 1
    return None


get_sddc_data()

def build_sddc_list():
    myHeader = {'csp-auth-token': data.sessiontoken}
    myURL = strProdURL + "/vmc/api/orgs/" + tenantID + "/sddcs"
    response = requests.get(myURL, headers=myHeader)
    json_response = response.json()
    del sddc_list[:]
    if response.status_code == 200:
        for i in json_response:
            sddc_list.append(i['name'])
        return sddc_list
    else:
        print(response.status_code)
        print(response.json())
    return


def add_sddc_hosts(hosts):
    myHeader = {'csp-auth-token': data.sessiontoken}
    myURL = strProdURL + "/vmc/api/orgs/" + tenantID + "/sddcs/" + sddcID + "/esxs"
    strRequest = {"num_hosts": hosts}
    response = requests.post(myURL, json=strRequest, headers=myHeader)
    if response.status_code != 202:
        print(response.status_code)
        print(response.json())
    # time.sleep(10)
    return


def remove_sddc_hosts(hosts):
    myHeader = {'csp-auth-token': data.sessiontoken}
    myURL = strProdURL + "/vmc/api/orgs/" + tenantID + "/sddcs/" + sddcID + "/esxs?action=remove"
    strRequest = {"num_hosts": hosts}
    response = requests.post(myURL, json=strRequest, headers=myHeader)
    if response.status_code != 202:
        print(response.status_code)
        print(response.json())
    # time.sleep(10)
    return str(response.status_code)

#------------------ Post something to Slack
# Slack API info can be found at https://api.slack.com/incoming-webhooks
# https://api.slack.com/tutorials/slack-apps-hello-world
# Need to create a new App using the Slack API App Builder -- it only needs to do one thing - catch a webhook

def postSlack(slackURL, slackJSONData):
    slackData = json.dumps(slackJSONData)
    myHeader = {'Content-Type': 'application/json'}
    response = requests.post(slackURL, slackData, headers=myHeader)
    if response.status_code != 200:
        raise ValueError(
            'Request to slack returned an error %s, the response is:\n%s'
            % (response.status_code, response.text)
        )
    return

# --------------- Helpers that build all of the responses ----------------------


def build_speechlet_response(title, output, reprompt_text, should_end_session):
    """Build a speechlet JSON representation of the title, output text,
    reprompt text & end of session"""

    return {'outputSpeech': {'type': 'PlainText', 'text': output},
        'card': {'type': 'Simple', 'title': CardTitlePrefix + " - " + title, 'content': output},
        'reprompt': {'outputSpeech': {'type': 'PlainText', 'text': reprompt_text}},
        'shouldEndSession': should_end_session}


def build_response(session_attributes, speechlet_response):
    # Build the full response JSON from the speechlet response
    return {'version': '1.0', 'sessionAttributes': session_attributes, 'response': speechlet_response}


# --------------- Functions that control the skill's behavior ------------------

def get_welcome_response():
    card_title = "Hello"
    session_attributes = {}
    speech_output = "Welcome to the VMware Cloud on AWS demo... Ask me."
    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = "I repeat: Welcome to the VMware Cloud on AWS demo... Ask me."
    should_end_session = False
    return build_response(session_attributes,
                          build_speechlet_response(card_title, speech_output, reprompt_text, should_end_session))


def handle_session_end_request():
    card_title = "Session Ended"
    session_attributes = {}
    speech_output = "Thanks for your time and have a nice day! "
    # Setting this to true ends the session and exits the skill.
    should_end_session = True
    return build_response(session_attributes, build_speechlet_response(card_title, speech_output, None, should_end_session))


def please_wait():
    card_title = "Wait"
    session_attributes = {}
    speech_output = "OK."
    reprompt_text = "I am waiting..."
    return build_response(session_attributes, build_speechlet_response(card_title, speech_output, reprompt_text, False))


def get_sddc_list():
    card_title = "SDDClist"
    session_attributes = {}
    the_list = build_sddc_list()
    speech_output = "This is the list of SDDCs in your organization: " + (", ".join(the_list))
    if slack_channel:
        jsonSlackMessage = {'text': "```List of SDDCs in your organization: \n" + (", ".join(the_list)) + "```"}
        postSlack(slackURL, jsonSlackMessage)
    return build_response(session_attributes, build_speechlet_response(card_title, speech_output, "Ask me ...", False))


def get_sddc_name():
    card_title = "SDDCname"
    session_attributes = {}
    speech_output = "Your SDDC name is: " + data.sddc_name + "... It's deployed in " + data.sddc_region + " region."
    if slack_channel:
        jsonSlackMessage = {'text': "```SDDC name: " + data.sddc_name + "\nDeployed in: " + data.sddc_region + "```"}
        postSlack(slackURL, jsonSlackMessage)
    return build_response(session_attributes, build_speechlet_response(card_title, speech_output, None, False))


def get_sddc_status():
    card_title = "SDDCstatus"
    session_attributes = {}
    get_sddc_data()
    speech_output = "Your SDDC status is: " + data.sddc_status + "..." + \
        "You have " + str(data.sddc_hosts) + " hosts... They are deployed in " + data.sddc_region + " region." + \
        "... They form a cluster called: " + data.sddc_cluster
    if slack_channel:
        jsonSlackMessage = {'text': "```SDDC status: " + data.sddc_status + "\n" + \
            "You have " + str(data.sddc_hosts) + " hosts\nDeployed in: " + data.sddc_region + \
            "\ncluster Name: " + data.sddc_cluster + "```"}
        postSlack(slackURL, jsonSlackMessage)
    return build_response(session_attributes, build_speechlet_response(card_title, speech_output, "Ask me ...", False))


def add_hosts(intent, session):
    card_title = intent['name']
    session_attributes = {}
    reprompt_text = "Ask me..."
    should_end_session = False

    if 'value' in intent['slots']['Num']:
        hosts = intent['slots']['Num']['value']
        add_sddc_hosts(hosts)
        if slack_channel:
            jsonSlackMessage = {'text': "```Adding " + hosts + " hosts.```"}
            postSlack(slackURL, jsonSlackMessage)
        speech_output = "OK. I am adding " + hosts + " hosts."
    else:
        speech_output = "I know numbers up to five. Please try again."
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def remove_hosts(intent, session):
    card_title = intent['name']
    session_attributes = {}
    reprompt_text = "Ask me..."
    should_end_session = False

    if 'value' in intent['slots']['Num']:
        hosts = intent['slots']['Num']['value']
        result = remove_sddc_hosts(hosts)
        if result == "400":
            speech_output = "Sorry, the minimum size for a cluster is 4 hosts."
            return build_response(session_attributes,
                                  build_speechlet_response(card_title, speech_output, reprompt_text, should_end_session))
        if slack_channel:
            jsonSlackMessage = {'text': "```Removing " + hosts + " hosts.```"}
            postSlack(slackURL, jsonSlackMessage)
        speech_output = "OK. I am removing  " + hosts + " hosts."
    else:
        speech_output = "I know numbers up to five. Please try again."
    return build_response(session_attributes,
                          build_speechlet_response(card_title, speech_output, reprompt_text, should_end_session))


def enable_slack_channel(intent, session):
    card_title = "EnableSlack"
    session_attributes = {}
    speech_output = "Slack Channel Enabled."
    reprompt_text = "Ask me..."
    global slack_channel
    slack_channel = True
    jsonSlackMessage = {'text': "```Slack Channel enabled.```"}
    postSlack(slackURL, jsonSlackMessage)
    return build_response(session_attributes, build_speechlet_response(card_title, speech_output, reprompt_text, False))


def disable_slack_channel(intent, session):
    card_title = "DisableSlack"
    session_attributes = {}
    speech_output = "Slack Channel disabled."
    reprompt_text = "Ask me..."
    global slack_channel
    slack_channel = False
    jsonSlackMessage = {'text': "```Slack Channel disabled.```"}
    postSlack(slackURL, jsonSlackMessage)
    return build_response(session_attributes, build_speechlet_response(card_title, speech_output, reprompt_text, False))
# --------------- Events ------------------


def on_session_started(session_started_request, session):
    """Called when the session starts"""
    print(
        "on_session_started requestId=" + session_started_request['requestId'] + ", sessionId=" + session['sessionId'])


def on_launch(launch_request, session):
    """Called when the user launches the skill without specifying what they want """

    print("on_launch requestId=" + launch_request['requestId'] + ", sessionId=" + session['sessionId'])
    # Dispatch to your skill's launch
    return get_welcome_response()


def on_intent(intent_request, session):
    """ Called when the user specifies an intent for this skill """

    print("on_intent requestId=" + intent_request['requestId'] + ", sessionId=" + session['sessionId'])
    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']

    # Dispatch to your skill's intent handlers
    if intent_name == "Wait":
        return please_wait()
    elif intent_name == "SDDClist":
        return get_sddc_list()
    elif intent_name == "SDDCname":
        return get_sddc_name()
    elif intent_name == "SDDCstatus":
        return get_sddc_status()
    elif intent_name == "ADDhosts":
        return add_hosts(intent, session)
    elif intent_name == "REMOVEhosts":
        return remove_hosts(intent, session)
    elif intent_name == "EnableSlack":
        return enable_slack_channel(intent, session)
    elif intent_name == "DisableSlack":
        return disable_slack_channel(intent, session)
    elif intent_name == "AMAZON.HelpIntent":
        return get_welcome_response()
    elif intent_name == "AMAZON.CancelIntent" or intent_name == "AMAZON.StopIntent":
        return handle_session_end_request()
    else:
        raise ValueError("Invalid intent")


def on_session_ended(session_ended_request, session):
    """ Called when the user ends the session. Is not called when the skill returns should_end_session=true """
    print("on_session_ended requestId=" + session_ended_request['requestId'] + ", sessionId=" + session['sessionId'])

# --------------- Main handler ------------------


def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    print("event.session.application.applicationId=" + event['session']['application']['applicationId'])

    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']}, event['session'])
    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])
