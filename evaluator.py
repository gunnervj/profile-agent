from openai import OpenAI
from pydantic import BaseModel
import os


class Evaluation(BaseModel):
    is_acceptable: bool
    feedback: str


class Evaluator:
    
    def __init__(self, persona_name, summary, linkedin):
        self.gemini = OpenAI(
            api_key=os.getenv("GOOGLE_API_KEY"),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/")
        self.persona_name = persona_name
        self.summary = summary
        self.linkedin = linkedin

    def evaluator_system_prompt(self):
        evaluator_system_prompt = f"""
        You are an evaluator that decides whether a response to a user's question is acceptable or not.
        You are provided with a conversation between a user and an agent. The agent is playing the role of {self.persona_name} and
        is representing {self.persona_name} for interactions on the website.
        The agent has been instructed to be professional, engaging and concise in their answers as if talking to a potential client or future employer who came across the website.
        The Agent has been provided with the content on {self.persona_name} in the form of their summary and LinkedIn profile. Here is the
        information:
        """
        evaluator_system_prompt += f"\n\n ## Summary: \n {self.summary} \n\n ## LinkedIn: \n {self.linkedin}\n\n"
        evaluator_system_prompt += f"With this context, please evaluate the latest response, replying with whether the response is acceptable and your feedback."
        return evaluator_system_prompt

    def evaluator_user_prompt(self, reply, message, history):
        user_prompt = f"Here is the conversation between the user and the agent \n\n{history}\n \n"
        user_prompt += f"Here is the latest message from the user:\n\n{message}\n\n"
        user_prompt += f"Here is the latest response from the agent: \n\n {reply} \n\n"
        user_prompt += "Please evaluate the response, replying with whether it is acceptable and your feedback"
        return user_prompt

    def evaluate(self, reply, message, history) -> Evaluation:
        messages = [{"role": "system", "content": self.evaluator_system_prompt()}] + [{"role": "user", "content": self.evaluator_user_prompt(reply, message, history)}]
        response = self.gemini.beta.chat.completions.parse(model="gemini-2.0-flash", messages=messages, response_format=Evaluation)
        return response.choices[0].message.parsed

