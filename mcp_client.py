
import sys
import asyncio
from ollama import AsyncClient



from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

### TOOLS

# --- Fonction 1 : Lister les outils ---
async def get_tools_from_mcp():
    # Define the server parameters
    params = StdioServerParameters(
        command=sys.executable,
        args=["mcp_server.py"],
    )


    # Connect to the MCP server and open a session
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            # Initialize the session
            await session.initialize()

            # Ask the server what tools it provides
            response = await session.list_tools()

             # Display the available tools
            # print("Connected to MCP server!")
            # print("Available tools:")
            # for tool in response.tools:
            #    print(f" - {tool.name}: {tool.description}")
                
            return response.tools

# --- Fonction 2 : Estimer les vaccins (avec argument population) ---
async def call_mcp_tool(tool_name:str, arguments:dict)->str:
    params = StdioServerParameters(
        command = sys.executable,
        args = ["mcp_server.py"]
    )        

    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()

            # Call the oral polio vaccine estimator tool
            result = await session.call_tool(tool_name, arguments)

            # Extract and print the text content of the server response
            text_content = result.content[0].text

            # print(f"OPV estimation: {text_content}")
            return str(text_content)

        
### PROMPTS

async def list_prompts():
    """List all available prompts from the MCP server."""
    params = StdioServerParameters(command=sys.executable, args=["mcp_server.py"])

    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()

            # List available prompts
            prompts = await session.list_prompts()
            print(f"Available prompts: {[p.name for p in prompts.prompts]}")

            return prompts.prompts

async def read_prompt(user_input: str, prompt_name: str = "opv_estimator_prompt") -> str:
    """Retrieve a prompt from the MCP server with user input."""
    params = StdioServerParameters(command=sys.executable, args=["mcp_server.py"])

    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()

            # Retrieve the prompt with the user's input
            # La règle d'or pour le MCP :
            # Dans le Model Context Protocol, les clés du dictionnaire arguments côté client doivent impérativement correspondre nom pour nom aux arguments définis dans la fonction Python du serveur.
            # ici côté client arguments={"estimation_request": user_input} == côté server def opv_estimator_prompt(estimation_request:str) -> str:
            
            prompt = await session.get_prompt(prompt_name, arguments={"estimation_request": user_input})

            # Print the full prompt text (template + user request)
            text = prompt.messages[0].content.text
            print(text)
            return text

#### RESOURCES

async def list_resources():
    """List all available resources from the MCP server."""
    params = StdioServerParameters(command=sys.executable, args=["mcp_server.py"])

    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            # Get the list of resources
            response = await session.list_resources()

            print("Available resources:")
            # Print each resource's URI, name, and description
            for resource in response.resources:
                print(f" - {resource.uri}")
                print(f"   Name: {resource.name}")
                print(f"   Description: {resource.description}")

            return response.resources


# Define an async function for reading MCP resources
async def read_resource(resource_uri: str):
    """Read a specific resource by URI."""
    params = StdioServerParameters(
        command=sys.executable,
        args=["mcp_server.py"],
    )

    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()

            print(f"Reading resource: {resource_uri}")
            # Read the resource from the session context
            resource_content = await session.read_resource(resource_uri)

            # Print the contents of each resource
            for content in resource_content.contents:
                print(f"\nContent ({content.mime_type}):")
                print(content.text)

            return resource_content


async def get_context_from_mcp(user_query: str) -> tuple[str, str]:
    """Fetch resource content and prompt text from the MCP server."""
    params = StdioServerParameters(command=sys.executable, args=["mcp_server.py"])

    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()

            # Read the resource (supported currencies)
            resource_result = await session.read_resource("config://vaccine-default-params-value")
            resource_text = resource_result.contents[0].text

            # Get the prompt with the user's query
            prompt_result = await session.get_prompt("opv_estimator_prompt",
                arguments={"estimation_request": user_query})
            prompt_text = prompt_result.messages[0].content.text

            return resource_text, prompt_text

###############################################


async def call_llama_llm(user_query: str):
    """Call Llama with MCP tools using Ollama."""
    
    print(f"\nUser: {user_query}\n")

    mcp_tools = await get_tools_from_mcp()
    
    # 1. Adaptation du format des outils (Anthropic 'input_schema' -> Ollama 'parameters')
    llama_tools = []
    for tool in mcp_tools:
        llama_tool = {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.input_schema,
            }
        }
        llama_tools.append(llama_tool)
    
    # 2. Initialisation du client Ollama (cible le serveur local)
    # Note: Si localhost ne répond pas depuis WSL, remplacez par 'http://127.0.0.1:11434'
    client = AsyncClient(host='http://localhost:11434')
    MODEL = "llama3.2" 

    messages = [{"role": "user", "content": user_query}]

    # Premier tour : Envoi de la question et des outils disponibles
    response = await client.chat(
        model=MODEL,
        messages=messages,
        tools=llama_tools,
    )

    assistant_message = response['message']
    messages.append(assistant_message)

    # 3. Vérification si Llama demande l'exécution d'un outil
    if assistant_message.get('tool_calls'):
        # On extrait le premier appel de fonction requis par le modèle
        tool_call = assistant_message['tool_calls'][0]
        name = tool_call['function']['name']
        args = tool_call['function']['arguments']

        print(f"Model decided to call: {name}")
        print(f"Arguments: {args}\n")

        # Appel de votre outil MCP local
        result = await call_mcp_tool(name, args)

        # 4. Ajout du résultat de l'outil dans l'historique des messages
        messages.append({
            "role": "tool",
            "name": name,
            "content": str(result)
        })

        # Second tour : Llama formule la réponse finale à partir du résultat de l'outil
        followup = await client.chat(
            model=MODEL,
            messages=messages,
            tools=llama_tools,
        )

        final_text = followup['message']['content']
        print(f"\nAssistant: {final_text}")
        return str(final_text)

    else:
        text = assistant_message.get('content', '')
        print(f"\nAssistant: {text}")
        return str(text)

    

async def call_llama_llm_with_context(user_query: str):
    """Call the LLM with resource and prompt context from MCP."""
    resource_text, prompt_text = await get_context_from_mcp(user_query)

    # Combine the resource and prompt text
    full_prompt = prompt_text + "\n\nSupported default values:\n" + resource_text

    # Combine the resource and prompt text
    full_prompt = prompt_text + "\n\nSupported default values:\n" + resource_text

    # 1. Initialisation du client Ollama (cible le serveur local)
    # Note: Si localhost ne répond pas depuis WSL, remplacez par 'http://127.0.0.1:11434'
    client = AsyncClient(host='http://localhost:11434')
    mcp_tools = await get_tools_from_mcp() 

    # 2. Adaptation du format des outils (Anthropic 'input_schema' -> Ollama 'parameters')
    llama_tools = []
    for tool in mcp_tools:
        llama_tool = {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.input_schema,
            }
        }
        llama_tools.append(llama_tool)

    messages = [{"role": "user", "content": full_prompt}]
    MODEL = "llama3.2" 

    # Premier appel au modèle Llama 3.2
    response = await client.chat(
        model=MODEL,
        messages=messages,
        tools=llama_tools,
    )
   
    assistant_message = response['message']
    messages.append(assistant_message)


    message = response.get("message", {})

    # Vérifie si le modèle demande l'appel d'un outil (tool call)
    if message.get("tool_calls"):
        # Ajout de la réponse de l'assistant à l'historique des messages
        messages.append(message)
        
        for tool_call in message["tool_calls"]:
            tool_name = tool_call["function"]["name"]
            tool_args = tool_call["function"]["arguments"]
            
            # Exécution de l'outil MCP
            result = await call_mcp_tool(tool_name, tool_args)
            
            # Ajout du résultat de l'outil dans l'historique
            messages.append({
                "role": "tool",
                "content": str(result),
            })


        # Second appel au modèle avec le résultat de l'outil
        followup = await client.chat(
            model="llama3.2",
            messages=messages,
            tools=llama_tools,
        )
        
        final_text = followup.get("message", {}).get("content", "")
        if final_text:
            print(f"\nAssistant: {final_text}")
            return str(final_text)
    else:
        # Réponse textuelle simple (ex: demande ambiguë nécessitant des précisions)
        text = message.get("content", "")
        print(f"\nAssistant: {text}")
        return str(text)

        



# N'oubliez pas de lancer Ollama sur Windows et de faire un `ollama pull llama3.2` avant

########
#print("=== Ambiguous request (prompt asks for clarification) ===")
#asyncio.run(call_llama_llm_with_context("How many 20-dose vaccine vials are needed for a polio vaccination campaign"))
print("\n=== Unambiguous request (model calls tool) ===")
asyncio.run(call_llama_llm_with_context("How many 20-dose vaccine vials are needed for a polio vaccination campaign for a total population of 78,921"))
############

# asyncio.run(call_llama_llm("How many 20-dose vaccine vials are needed for a polio vaccination campaign for a total population of 78,921 inhabitants?"))
# asyncio.run(get_context_from_mcp("How many vials for a total population of 78921"))
# asyncio.run(read_resource("config://vaccine-default-params-value"))
# asyncio.run(list_resources())    
# asyncio.run(list_prompts())
# asyncio.run(call_mcp_tool("polio_vaccine_estimator",{"population": 78921}))
# asyncio.run(read_prompt(user_input="Estimates the total number of oral polio vaccine for a population of 78921"))