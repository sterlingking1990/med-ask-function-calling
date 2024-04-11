import os
from dotenv import load_dotenv
load_dotenv()
#API_KEY = os.getenv("API_KEY")
AUTH_KEY = os.getenv("AUTH_KEY")
BASE_URL = os.getenv("BASE_URL")
import requests
import vertexai
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials


med_service = "med-ask-service.json"
credentials = Credentials.from_service_account_file(med_service,scopes=['https://www.googleapis.com/auth/cloud-platform'])
if(credentials.expired):
    credentials.refresh(Request())

vertexai.init(
    project="serverless-rest-4b558",
    location="us-central1",credentials=credentials
)

from vertexai.generative_models import(FunctionDeclaration,GenerativeModel,Part,Tool,)

#1. model initialization 
model = GenerativeModel("gemini-1.0-pro",generation_config={"temperature":0,})
chat = model.start_chat(response_validation=False,history=[])

#2. define the actual get med details function 

def pharmacy_product_detail(parameters):
    # lets use a fictional api; although you can use your companies api here
    url = f"{BASE_URL}/pharmacy/pharmacy_product_list/kenya?page=1&minimum_price=10&maximum_price=200"
    response = requests.get(url,params=parameters,headers={'x-api-key':AUTH_KEY})
    if response.status_code == 200:
        data = response.json()
        pharmacy_products = data.get("pharmacy_products",[])
        if pharmacy_products:  # Check if the array is not empty
            return pharmacy_products[0]  # Return the first object in the array
        else:
            return {"error": "No pharmacy products found"}
    else:
        return {"error": f"API error: {response.status_code}"}
    
tool = Tool(function_declarations=[
    FunctionDeclaration(
        name="pharmacy_product_detail",
        description= "return the detail of a pharmacy product based on the search word or return only first page list if no search word found",
        parameters={
            "type": "object",
            "properties": {
                "search_word": {
                    "type": "string",
                    "description": "The search word for returning pharmacy product detail"
                    },
                "page":{
                    "type":"integer",
                    "description":"the current page of the pharmacy list"
                },
                "minimum_price":{
                    "type":"integer",
                    "description":"the minimum filtered price to determine the pharmacy listing"
                },
                "maximum_price":{
                    "type":"integer",
                    "description": "the maximum filtered price to determine pharmacy listing"
                }
                },
            }
        )
    ]
)
# here is now our function_handler
function_handler = {
  "pharmacy_product_detail": pharmacy_product_detail
}

#re-assign our model with our tools setup
model = GenerativeModel("gemini-1.0-pro",generation_config={"temperature":0,},tools=[tool])
chat = model.start_chat(response_validation=False, history=[])

prompt = "what is the available_quantity of new product 9"
response = chat.send_message(prompt)
function_call = response.candidates[0].content.parts[0].function_call
# you can decide to print the function_call to see what response came back from Gemini
print(function_call)


if function_call.name in function_handler:
        function_name = function_call.name
        #get the arg and pass it unto the tool_name
        args = {key: value for key,value in function_call.args.items()}
    
        function_response = function_handler[function_name](args)
    
        #use the tool and its argument to answer the question 
        response = chat.send_message(
            Part.from_function_response(name=function_name,
                                    response={
                                        "content": function_response
                                    })
        )
        chat_response = response.candidates[0].content.parts[0].text
        print(chat_response)
else:
    #if it didnt find any tool for the prompt, we return Gemini default
    #response 
    print(response.text)
    
