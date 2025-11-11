from dotenv import load_dotenv
from httpx import request

import gradio as gr
import os
from persona import Persona

load_dotenv(override=True)

def push(text):
    request.post("https://api.pushover.net/1/message.json",
    data={
        "token": os.getenv("PUSHOVER_TOKEN"),
        "user": os.getenv("PUSHOVER_USER"),
        "message": text
        }   
    )
persona = Persona("Vijay Nair", "me/Profile.pdf", "me/summary.txt")
gr.ChatInterface(persona.chat, type="messages").launch()