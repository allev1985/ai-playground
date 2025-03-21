from icecream import ic
from dotenv import load_dotenv
from agent import Agent
import yaml
import os

load_dotenv()

apiKey = os.getenv("API_KEY")
model = os.getenv("CLAUDE_MODEL")

with open('config/prompts.yml', 'r') as prompts:
    yamlDict = yaml.safe_load(prompts)

ic(yamlDict)


agent = Agent()
agent.initialise(yamlDict, model, apiKey)

