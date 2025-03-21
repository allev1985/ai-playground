from icecream import ic
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.prompts.chat import SystemMessagePromptTemplate, HumanMessagePromptTemplate, AIMessagePromptTemplate
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_core.messages import HumanMessage
from langchain_anthropic import ChatAnthropic
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
import json

class Agent(): 
    MEMORY_KEY = 'chat_history'
    _instructions = None
    _chat = None
    _memory = None
    _memoryEnabled = True

    def __init__(self):
        pass
    
    def enable_memory(self):
        self._memoryEnabled = True
    
    def disable_memory(self): 
        self._memoryEnabled = False

    def _set_instruction_template(self, systemPrompt, interactionPrompts):
        instructionsMessages = [
            SystemMessagePromptTemplate.from_template(systemPrompt)
        ]
        if self._memoryEnabled:
            instructionsMessages.append(MessagesPlaceholder(variable_name=self.MEMORY_KEY))
        for interaction in interactionPrompts:
            if interaction['type'] == 'human':
                instructionsMessages.append(HumanMessagePromptTemplate.from_template(interaction["template"]))
            else:
                instructionsMessages.append(AIMessagePromptTemplate.from_template(interaction["template"])) 
        instructionsMessages.append(HumanMessagePromptTemplate.from_template("{input}"))
        return ChatPromptTemplate.from_messages(instructionsMessages)
    
    def _init_agent(self, instructions, model=None, apiKey=None):
        if 'interactions' not in instructions:
            instructions['interactions'] = []
        self._instructions = self._set_instruction_template(instructions["system"], instructions["interactions"])
        
        if self._memoryEnabled:
            self._memory = ChatMessageHistory()
            
        self._chat = ChatAnthropic(
            model=model, 
            temperature=0.7,
            anthropic_api_key=apiKey 
        )
    
    def initialise(self, instructions, model=None, apiKey=None):
        self._init_agent(instructions, model, apiKey)
        
        # Create the chain by connecting prompt and model
        chain = self._instructions | self._chat
            
        # Create a session getter function for the memory
        def get_session_history(session_id):
            return self._memory if self._memoryEnabled else None
        
        # Wrap the chain with message history handling
        chain_with_history = RunnableWithMessageHistory(
            chain,
            get_session_history,
            input_messages_key="input",
            history_messages_key=self.MEMORY_KEY,
            output_messages_key="output"
        )
        
        # Configure with default values
        configurable_chain = chain_with_history.with_config(
            configurable={"verbose": True},
        )
            
        return configurable_chain

    def _format_response(self, response):
        strParser = StrOutputParser()
        jsonParser = JsonOutputParser()
        strOutput = strParser.parse(response)
        
        try: 
            jsonOuput = jsonParser.parse(strOutput)
            return json.dumps(jsonOuput, indent=2)
        except:
            return strOutput
        
    def invoke(self, chain, input_text, session_id="default", **kwargs):
        """
        Invoke the chain with the given input
        """
        input_dict = {
            "session_id": session_id,
            "input": input_text,
            **kwargs
        }
        ic(input_dict)

        response = chain.invoke(
            {"input": input_text},
            **kwargs,
            config={"configurable": {"session_id": session_id}}
        )
        ic(response)
        return self._format_response(response.content)