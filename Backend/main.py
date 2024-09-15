"""
How to start Flask server
Just use the python keyword and then the main file
Open a web browser
Example: http://127.0.0.1:5000/test
"""

from flask import Flask
import json
import openai
from datetime import datetime
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

@app.route("/test/")
def test():
    return { "None": "Test successful" }

# typeform
api_key = 'tfp_3ZcbVwoTezAB5RmojBdFySu3NSd5jTtFPbAFyLEgu4MP_3sqab6KCypM3zo'
form_id = 'Q7SYhh8n'

client = openai.OpenAI()
prompt_template = "You are a doctor. Inquire about the patient's **current symptoms** by asking open-ended questions like, How have you been feeling lately? or Can you describe any symptoms or concerns you have right now? If needed, ask follow-up questions to gather more specific details about the symptoms, such as duration, intensity, or any recent changes. After gathering the necessary information, thank the patient for their time and reassure them that the details will be forwarded to the doctor. Make all of your response short: 1-3 sentences."

def user_exists(username):
    with open("users/users.json", "r") as file:
        users = json.load(file)
    return username in users

@app.route("/get_history/<username>")
def get_history(username):
    with open(f"users/{username}/history.json", "r") as file:
        history = json.load(file)
        return { 0: history }

@app.route("/add_user/<username>/<JSON>")
def add_user(username, JSON):
    filepath = lambda x: f"users/{username}/{x}.json"
    os.makedirs(os.path.dirname(filepath(username)), exist_ok=True)
    with open(filepath(username), "w") as file:
        json.dump(json.loads(JSON), file, indent = 4)
    with open(filepath("history"), "w") as file:
        json.dump({}, file, indent = 4)
    return JSON

@app.route("/edit_user/<username>/<JSON>")
def edit_user(username, JSON):
    filepath = f"users/{username}/{username}.json"
    if os.path.exists(filepath):
        with open(filepath, "r") as file:
            dict = json.load(file)

        JSON = json.loads(JSON)
        for key in JSON.keys():
            dict[key] = JSON[key]

        with open(f"users/{username}/{username}.json", "w") as file:
            json.dump(dict, file, indent = 4)
        return "OK"

def generate_response(input, prompt):
    response = client.chat.completions.create(
            model="gpt-4o",
            temperature = 0.8,
            #the response_format parameter seems to reduce output quality
            #response_format={ "type": "json_object" }, 
            messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": input}
            ]
        )
    
    return response.choices[0].message.content

@app.route("/get_conversation/<username>/<index>/<proportion>")
def get_conversation(username, index, proportion = 1):
    with open(f"users/{username}/{index}.json", "r") as file:
        conversation = json.load(file)
        if proportion == 1:
            return { 0: list(conversation.values()) }
        return { 0: generate_response(str(list(conversation.values())), f"Summarize the input to {proportion} of the original length. ") }

@app.route("/one_on_one/<username>/<index>/<message>")
def one_on_one(username, index, message):
    add_message(username, index, message)
    message = get_next_message(username, index)
    return message

def get_next_message(username, index):
    conversation = get_conversation(username, index)[0]
    message = generate_response(str(conversation), prompt_template)
    add_message(username, index, message)
    return { 0: message }

def add_message(username, index, message):
    if not os.path.exists(f"users/{username}/{index}.json"):
        history = get_history(username)[0]
        history[index] = datetime.now().strftime("%Y-%m-%d") + " " + generate_response(message, "Summarize the following. ")
    
        with open(f"users/{username}/history.json", "w") as file:
            json.dump(history, file, indent=4)

        conversation = dict()
    else:
        with open(f"users/{username}/{index}.json", "r") as file:
            conversation = json.load(file)

    now = datetime.now()
    conversation[f"{now.strftime("%Y-%m-%d %H:%M:%S")} {(now.microsecond // 1000):03d}"] = message
    with open(f"users/{username}/{index}.json", "w") as file:
        json.dump(conversation, file, indent = 4)
    
    return "OK"

@app.route("/registration/")
def registration():
    url = f'https://api.typeform.com/forms/{form_id}/responses'
    headers = { 'Authorization': f'Bearer {api_key}' }
    questions = ["first_name", "last_name", "gender", "age", "allergies", "medication", "username", "password"]

    response = requests.get(url, headers=headers).json()
    responses = response["items"][0]["answers"]
    unroll = lambda x: unroll(el) if isinstance((el := list(x.values())[-1]), dict) else el
    arr = { questions[i]: unroll(elem) for i, elem in enumerate(responses) }
    return arr

@app.route("/get_profile/<username>")
def get_profile(username):
    with open(f"users/{username}/{username}.json", "r") as file:
        data = json.load(file)
    return { 0: data }

@app.route("/get_transcript/<username>/<indices>")
def get_transcript(username, indices):
    transcript = {}
    for i in indices:
        with open(f"users/{username}/{i}.json", "r") as file:
            conversation = json.load(file)
        transcript[i] = conversation
    return { 0: transcript }

@app.route("/sign_in/<username>/<password>")
def sign_in(username, password):
    with open(f"users/users.json", "r") as file:
        users = json.load(file)
        if username in users and users[username] == password:
            return { 0: "SUCCESS" }
        return { 0: "FAIL" }

@app.route("/sign_up/<username>/<password>")
def sign_up(username, password):
    with open(f"users/users.json", "r") as file:
        users = json.load(file)
        if username in users:
            return { 0: "FAIL" }
        
        add_user(username, json.dumps(registration()))
        return { 0: "SUCCESS" }

def test_openai():
    # edit_user("joesmith", "{'first name': 'bobby', 'last name':'smith'}")

    # fraud = registration()
    # add_user("fraud", json.dumps(fraud))

    # first_name = input("first name: ")
    # last_name = input("last name: ")
    # username = input("username: ")
    # password = input("password: ")
    # age = input("age: ")
    # gender = input("gender: ")

    # user = { "first name": first_name, "last name": last_name, "username": username, "password": password, "age": age, "gender": gender }
    # add_user(user["username"], json.dumps(user))
    
    username = "joesmith"
    index = 0
    print("Hello! How can I help you today?")
    while (answer := input()) != "None":
        add_message(username, index, answer)
        response = get_next_message(username, index)[0]
        print(response)
    print(get_conversation(username, index, 0.25))

if __name__ == "__main__":
    # test_openai()
    app.run(port=5000, host="0.0.0.0")
