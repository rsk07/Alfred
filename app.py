# -*- coding: utf-8 -*-


import os
import sys
import json

import requests
from flask import Flask, request

from bs4 import BeautifulSoup
import requests
import apiai
import pickle
import random
import re

app = Flask(__name__)


popular_choice = ['motivational', 'life', 'positive', 'friendship', 'success', 'happiness', 'love']

def get_quotes(type, number_of_quotes=1):
    url = "http://www.brainyquote.com/quotes/topics/topic_" + type + ".html"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    quotes = []
    for quote in soup.find_all('a', {'title': 'view quote'}):
        quotes.append(quote.contents[0])

    if quotes == [] :
        return 'Oops, could not find any quote! Try some other general topic. :)'
    random.shuffle(quotes)
    result = quotes[:number_of_quotes]
    return result[0]


def get_random_quote():
    result = get_quotes(popular_choice[random.randint(0, len(popular_choice) - 1)])
    return result

def chunkstring(string, length):
    return (string[0+i:length+i] for i in range(0, len(string), length))

def apiai_call(message):
    ai = apiai.ApiAI(os.environ["APIAI_CLIENT_ACCESS_TOKEN"])
    request = ai.text_request()
    request.query = message 
    response = request.getresponse()
    response_json = json.loads(response.read().decode('utf-8'))
    return response_json['result']['fulfillment']['speech']

def findmeme():
    url = "http://www.memecenter.com/search/big%20bang%20theory"
    links = []
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    
    for line in soup.find_all('img', class_ = "rrcont"):
        links.append(line.get('src'))
    
    url = "http://www.wapppictures.com/30-hilarious-memes-big-bang-theory/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    for line in soup.find_all('img', class_ = re.compile("aligncenter+")):
        links.append(line.get('src'))

    random.shuffle(links)

    return links


@app.route('/', methods=['GET'])
def verify():
    # when the endpoint is registered as a webhook, it must
    # return the 'hub.challenge' value in the query arguments
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == os.environ["VERIFY_TOKEN"]:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Hello world", 200


@app.route('/', methods=['POST'])
def webook():

    # endpoint for processing incoming messaging events

    data = request.get_json()
    log(data)  # you may not want to log every incoming message in production, but it's good for testing

    
    if data["object"] == "page":

        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:

                if messaging_event.get("message"):  # someone sent us a message

                    sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
                    recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID
                    message_text = ""
                    if "message" in messaging_event and "text" in messaging_event["message"]: # checking if there is any text in the message
                        message_text = messaging_event["message"]["text"]  # the message's text
                    else:
                        message_text = "Sticker!"

                    links = findmeme()
                    nameRegex = re.compile(r'quote (.*)')
                    mo = nameRegex.search(message_text.lower())
                    
                    if message_text.lower()=="i'm done":
                        type_message(sender_id)
                        send_message(sender_id, "Goodbye. If you require more of my assistance, don't hesitate and wake me up. It would be my honour to help you.")
            
                    elif message_text.lower()=="quote" or message_text.lower()=="quote!":
                        type_message(sender_id)
                        send_message(sender_id, str(get_random_quote()))
                        send_message(sender_id, "You can also type <quote> <topic> to get a quote related to that topic or press any button.")
                        quickreply(sender_id)

                    elif message_text.lower()=="meme" or message_text.lower()=="send me a meme" or message_text.lower()=="show me a meme":
                        type_message(sender_id)
                        random.shuffle(links)
                        sendmeme(sender_id, links)
                        quickreply(sender_id)

                    elif mo != None :
                        send_message(sender_id, str(get_quotes(mo.group(1))))
                        quickreply(sender_id)
                        
                    else:
                        type_message(sender_id)
                        send_message(sender_id, apiai_call(message_text))
                        quickreply(sender_id)


                    
                if messaging_event.get("delivery"):  # delivery confirmation
                    pass

                if messaging_event.get("optin"):  # optin confirmation
                    pass

                if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
                    pass

    return "ok", 200



def send_message(recipient_id, message_text):

    log("sending message to {recipient}: {text}".format(recipient=recipient_id, text=message_text))

    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        },
        #"sender_action":"typing_off"
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)

def sendmeme(recipient_id, links):

    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "attachment":{
                "type":"image",
                "payload":{
                    "url": links[0]
                }
            }
        }
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)


def type_message(recipient_id):

    log("typing bubbles message to {recipient}".format(recipient=recipient_id))

    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "sender_action":"typing_on"
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)

def quickreply(recipient_id):

    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": u'🖖'.encode('utf-8'),   
            "quick_replies":[
              {
                "content_type":"text",
                "title":"Quote",
                "payload":"NEW_JOKE"
              },
              {
                "content_type":"text",
                "title":"Meme",
                "payload":"MEME"
              },
              {
                "content_type":"text",
                "title":"I'm done",
                "payload":"DONE"
              }
            ]
        }
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)


def log(message):  # simple wrapper for logging to stdout on heroku
    print str(message)
    sys.stdout.flush()


if __name__ == '__main__':
    app.run(debug=True)
