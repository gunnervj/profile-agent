from openai import OpenAI
from pypdf import PdfReader

from evaluator import Evaluator

import json

from notification import Notification

class Persona:
    record_unknown_question_json = {
        "name": "record_unknown_question",
        "description": "Always use this tool to record any question that couldn't be answered as you didn't know the answer",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question that couldn't be answered"
                },
            },
            "required": ["question"],
            "additionalProperties": False
        }
    }
    tools = [{"type": "function", "function": record_unknown_question_json}]
    
    def __init__(self, name, profile_pdf_path, summary_text_path):
        self.openai = OpenAI()
        self.name = name
        self.reader = PdfReader(profile_pdf_path)
        self.linkedin = ""
        for page in self.reader.pages:
            text = page.extract_text()
            if text:
                self.linkedin += text
        with open(summary_text_path, "r") as file:
            self.summary = file.read()
        self.evaluator = Evaluator(self.name, self.summary, self.linkedin)
        self.notification = Notification()

    def system_prompt(self):
        system_prompt = f"""
                        you are acting as {self.name}. You are answering questions on your own wbsite, particularly questions
                        about your career, background, skills, interests, etc. Your responsibility is to
                        represent {self.name} for interactions on the website as faithfully as possible. You are git_revisiona summary of
                        {self.name}'s background and LinkedIn profile which you can use to answer questions.
                        Be professional, engagingand concise in your answers as if talking to a potential client or future employer who
                        came across the website. If you don't know the answer to any question, use your record_unknown_question tool to record the 
                        question that you couldn't answer, 
                        even if it's about something trivial or unrelated to career. 
                        """

        system_prompt += f"\n\n ## Summary: \n {self.summary} \n\n ## LinkedIn: \n {self.linkedin}\n\n"
        system_prompt += f"with this context, please chat with the user, always stay in charater as {self.name}."
        return system_prompt

    def rerun(self, reply, message, history, feedback):
        updated_system_prompt = self.system_prompt() + "\n\n## Previous answer rejected\nYou just tried to reply, but the quality control rejected your reply\n"
        updated_system_prompt += f"## Your attempted answer:\n{reply}\n\n"
        updated_system_prompt += f"## Reason for rejection:\n{feedback}\n\n"
        messages = [{"role": "system", "content": updated_system_prompt}] + history + [{"role": "user", "content": message}]
        response = self.openai.chat.completions.create(model="gpt-4o-mini", messages=messages)
        return response.choices[0].message.content

    def chat(self, message, history):
        messages = [{"role": "system", "content": self.system_prompt()}] + history + [{"role": "user", "content": message}]
        done = False
        while not done:
            response = self.openai.chat.completions.create(model="gpt-4o-mini", messages=messages, tools=self.tools)
            if response.choices[0].finish_reason == "tool_calls":
                message = response.choices[0].message
                tool_calls = message.tool_calls
                results = self.handle_tool_call(tool_calls)
                messages.append(message)
                messages.extend(results)
            else:
                done = True
        reply = response.choices[0].message.content
        print(reply)
        print("Performing evaluation..")
        evaluation = self.evaluator.evaluate(reply, message, history)
        if evaluation.is_acceptable:
            print("Passed evaluation - returning reply")
        else:
            print("Failed evaluation - retrying")
            print(evaluation.feedback)
            reply = self.rerun(reply, message, history, evaluation.feedback)       
        return reply

    def handle_tool_call(self, tool_calls):
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            print(f"Tool called: {tool_name}", flush=True)
            tool = getattr(self, tool_name, None)
            result = tool(**arguments) if tool else {}
            results.append({"role": "tool","content": json.dumps(result),"tool_call_id": tool_call.id})
        return results

    
    def record_unknown_question(self, question):
        self.notification.push(f"Recording {question}")
        return {"recorded": "ok"}