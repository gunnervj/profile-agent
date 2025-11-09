from pyexpat.errors import messages
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader
from pydantic import BaseModel

import gradio as gr
import os

load_dotenv(override=True)
openai = OpenAI()

gemini = OpenAI(
    api_key=os.getenv("GOOGLE_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

reader = PdfReader("me/Profile.pdf")

class Evaluation(BaseModel):
    is_acceptable: bool
    feedback: str

linkedin = ""

for page in reader.pages:
    text = page.extract_text()
    if text:
        linkedin += text

with open("me/summary.txt", "r") as file:
    summary = file.read()

name = "Vijay Nair"


system_prompt = f"""
you are acting as {name}. You are answering questions on your own wbsite, particularly questions
about your career, background, skills, interests, etc. Your responsibility is to
represent {name} for interactions on the website as faithfully as possible. You are git_revisiona summary of
{name}'s background and LinkedIn profile which you can use to answer questions.
Be professional, engagingand concise in your answers as if talking to a potential client or future employer who
came across the website. If you do not know the answer, say so.
"""

system_prompt += f"\n\n ## Summary: \n {summary} \n\n ## LinkedIn: \n {linkedin}\n\n"
system_prompt += f"with this context, please chat with the user, always stay in charater as {name}."


evaluator_system_prompt = f"""
You are an evaluator that decides whether a response to a user's question is acceptable or not.
You are provided with a conversation between a user and an agent. The agent is playing the role of {name} and
is representing {name} for interactions on the website.
The agent has been instructed to be professional, engaging and concise in their answers as if talking to a potential client or future employer who came across the website.
The Agent has been provided with the content on {name} in the form of their summary and LinkedIn profile. Here is the
information:
"""
evaluator_system_prompt += f"\n\n ## Summary: \n {summary} \n\n ## LinkedIn: \n {linkedin}\n\n"
evaluator_system_prompt += f"With this context, please evaluate the latest response, replying with whether the response is acceptable and your feedback."


def evaluator_user_prompt(reply, message, history):
    user_prompt = f"Here is the conversation between the user and the agent \n\n{history}\n \n"
    user_prompt += f"Here is the latest message from the user:\n\n{message}\n\n"
    user_prompt += f"Here is the latest response from the agent: \n\n {reply} \n\n"
    user_prompt += "Please evaluate the response, replying with whether it is acceptable and your feedback"
    return user_prompt

def evaluate(reply, message, history) -> Evaluation:
    messages = [{"role": "system", "content": evaluator_system_prompt}] + [{"role": "user", "content": evaluator_user_prompt(reply, message, history)}]
    response = gemini.beta.chat.completions.parse(model="gemini-2.0-flash", messages=messages, response_format=Evaluation)
    return response.choices[0].message.parsed

def rerun(reply, message, history, feedback):
    updated_system_prompt = system_prompt + "\n\n## Previous answer rejected\nYou just tried to reply, but the quality control rejected your reply\n"
    updated_system_prompt += f"## Your attempted answer:\n{reply}\n\n"
    updated_system_prompt += f"## Reason for rejection:\n{feedback}\n\n"
    messages = [{"role": "system", "content": updated_system_prompt}] + history + [{"role": "user", "content": message}]
    response = openai.chat.completions.create(model="gpt-4o-mini", messages=messages)
    return response.choices[0].message.content

def chat(message, history):
    message = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": message}]
    print(message)
    response = openai.chat.completions.create(model="gpt-4o-mini", messages=message)
    reply =response.choices[0].message.content
    print(reply)
    print("Performing evaluation..")
    evaluation = evaluate(reply, message, history)

    if evaluation.is_acceptable:
        print("Passed evaluation - returning reply")
    else:
        print("Failed evaluation - retrying")
        print(evaluation.feedback)
        reply = rerun(reply, message, history, evaluation.feedback)       
    return reply

gr.ChatInterface(chat, type="messages").launch()