import os, redis, time, json

from flask import Flask, render_template, request, session, make_response, jsonify
from flask_session import Session
from flask_socketio import SocketIO, emit

db = redis.Redis('localhost', decode_responses=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
socketio = SocketIO(app)

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
app.config["SECRET_KEY"] = "secret"
Session(app)

# Define message class
class Message:
    def __init__(self, sender, time, text):
        self.sender = sender
        self.time = time
        self.text = text

    def json(self):
        j = {"sender": self.sender,
                   "time": self.time,
                   "text": self.text}
        return json.dumps(j)

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/channels", methods=["POST"])
def channels():
    username = request.form.get("username")


    if not db.exists('channels'):
        # Create default channel list
        db.rpush('channels', "General")


    channels = db.lrange('channels', 0, -1)

    return render_template("channels.html", title="Channels", channels=channels, username=username, activeChannel="General")

# Create a new channel and push to websocket
@socketio.on("create channel")
def create_channel(channel_name):

    channels = db.lrange('channels', 0, -1)

    if (channel_name in channels):
        emit("channel already exists", channel_name, broadcast=True)

    else:
        # Update channels on Redis
        db.rpush('channels', channel_name)
        channels = db.lrange('channels', 0, -1)

        # Push message
        emit("channel added", channel_name, broadcast=True)


# Delete channel
@socketio.on("delete channel")
def delete_channel(channel_name):

    # Delete item from Redis
    db.lrem('channels', 1, channel_name)

    # Delete Redis list for this channel (i.e. clear all messages)
    db.delete(channel_name)

    # Push message
    emit("channel deleted", channel_name, broadcast=True)

# Open chat
@socketio.on("open chat")
def open_chat(channel_name):

    print("Opening chat"+channel_name)

    # Load chat history from Redis
    if db.exists(channel_name):
        chat = db.lrange(channel_name, 0, -1)

    else:
        chat = ""
    # Push message
    emit("chat opened", chat, broadcast=False)

# Send message
@socketio.on("send message")
def send_message(channel_name, message, username):

    m = Message(sender=username, time=time.time(), text=message)

    # Push message to Redis and trim store to 100 messages
    db.rpush(channel_name, m.json())
    db.ltrim(channel_name, -99, -1)

    # Push message
    emit("message received", m.json(), broadcast=True)

# Typing
@socketio.on("typing")
def send_message(channel_name, username, contents):
    d = {"username":username, "channel_name": channel_name, "contents": contents}
    data = json.dumps(d)

    # Push message
    emit("user is typing", data, broadcast=True)
