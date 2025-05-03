import os, json
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import asyncio
from google import genai
from concurrent.futures import TimeoutError
from rich.console import Console
from rich.panel import Panel

console = Console(stderr=True)

# Load environment variables from .env file
load_dotenv()

# Access your API key and initialize Gemini client correctly
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

max_iterations = 10
last_response = None
iteration = 0
iteration_response = []

async def generate_with_timeout(client, prompt, timeout=10):
    """Generate content with a timeout"""
    
    print("Initiating LLM generation...")
    try:
        # Convert the synchronous generate_content call to run in a thread
        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(
                None, 
                lambda: client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt
                )
            ),
            timeout=timeout
        )
        # print("LLM generation completed")
        # print('\n')
        return response
    
    except TimeoutError:
        # print("LLM generation timed out!")
        raise
    
    except Exception as e:
        # print(f"Error in LLM generation: {e}")
        raise

def reset_state():
    """Reset all global variables to their initial state"""
    global last_response, iteration, iteration_response
    last_response = None
    iteration = 0
    iteration_response = []

async def process_query(query: str) -> str:
    """Process a single query and return the response"""
    reset_state()
    
    try:
        # Create a single MCP server connection
        server_params = StdioServerParameters(
            command="python",
            args=["mcp_server.py"]
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Get available tools
                tools_result = await session.list_tools()
                tools = tools_result.tools
                # print(f"Number of tools: {len(tools)}")
                console.print(Panel(f"Number of tools: {len(tools)}", title="Number of tools", title_align="center", border_style="blue"))
                
                # Create system prompt with available tools
                tools_description = []
                for i, tool in enumerate(tools):
                    try:
                        params = tool.inputSchema
                        desc = getattr(tool, 'description', 'No description available')
                        name = getattr(tool, 'name', f'tool_{i}')
                        
                        if 'properties' in params:
                            param_details = []
                            for param_name, param_info in params['properties'].items():
                                param_type = param_info.get('type', 'unknown')
                                param_details.append(f"{param_name}: {param_type}")
                            params_str = ', '.join(param_details)
                        else:
                            params_str = 'no parameters'

                        tool_desc = f"{i+1}. {name}({params_str}) - {desc}"
                        tools_description.append(tool_desc)
                    except Exception as e:
                        tools_description.append(f"{i+1}. Error processing tool")
                
                tools_description = "\n".join(tools_description)
                # print("Successfully created tools description")

                system_prompt = f"""
                You are a reasoning-driven AI agent with access to tools and memory.
                Your job is to solve the user's request step-by-step by reasoning through the problem, selecting a tool if needed, and continuing until the FINAL_ANSWER is produced.

                Respond in **exactly one line** using one of the following formats:

                1. For function calls:
                FUNCTION_CALL: function_name|param1|param2|...
                Do not include parameter names in the function call. Only include the values.
                
                2. For final answers:
                FINAL_ANSWER: [output]

                For facilitating your work, you have access to the following tools:
                {tools_description}
    
                📏 IMPORTANT Rules:
                - 🚫 Do not include any empty string, empty rows, list of empty strings when calling tools such as bulk_update_cells
                - 🚫 Do NOT invent tools. Use only the tools listed above. Tool description has usage pattern, only use that.
                - 📄 If the question may relate to public/factual knowledge (like companies, people, places), use the `search_on_web` tool to look for the answer.
                - 🔁 Analyze that whether you have already got a good factual result from a tool, do NOT search again.
                - ❌ NEVER repeat tool calls with the same parameters unless the result was empty. When searching rely on first reponse from tools, as that is the best response probably.
                - ❌ NEVER output explanation text — only structured FUNCTION_CALL or FINAL_ANSWER.
                - 💡 If no tool fits or you're unsure, end with: FINAL_ANSWER: [unknown]
                - ⏳ You have 3 attempts. Final attempt must end with FINAL_ANSWER.
                """
                
                # print(f"System prompt: {system_prompt}")
                global iteration, last_response
                final_response = ""
                
                while iteration < max_iterations:
                    print(f"\n--- Iteration {iteration + 1} ---")
                    current_query = query if last_response is None else f"{query}\n\n{' '.join(iteration_response)}\nWhat should I do next?"

                    prompt = f"{system_prompt}\n\nQuery: {current_query}"
                    try:
                        response = await generate_with_timeout(client, prompt)
                        response_text = response.text.strip()
                        print(f"LLM Response: {response_text}")

                        for line in response_text.split('\n'):
                            line = line.strip()
                            if line.startswith("FUNCTION_CALL:"):
                                response_text = line
                                break
                        
                    except Exception as e:
                        return f"Error: {str(e)}"

                    if response_text.startswith("FUNCTION_CALL:"):
                        _, function_info = response_text.split(":", 1)
                        parts = [p.strip() for p in function_info.split("|")]
                        func_name, params = parts[0], parts[1:]
                        print(f"\nDEBUG: Split parts: {parts}")
                        print(f"\nDEBUG: Function name: {func_name}")
                        print(f"\nDEBUG: Raw parameters: {params}")

                        try:
                            tool = next((t for t in tools if t.name == func_name), None)
                            if not tool:
                                return f"Error: Unknown tool {func_name}"

                            print(f"\nDEBUG: Found tool: {tool.name}")
                            arguments = {}
                            schema_properties = tool.inputSchema.get('properties', {})
                            print(f"\nDEBUG: Schema properties: {schema_properties}")
                            for param_name, param_info in schema_properties.items():
                                if not params:
                                    return f"Error: Not enough parameters for {func_name}"
                                    
                                value = params.pop(0)
                                param_type = param_info.get('type', 'string')
                                
                                if param_type == 'integer':
                                    arguments[param_name] = int(value)
                                elif param_type == 'number':
                                    arguments[param_name] = float(value)
                                elif param_type == 'array':
                                    if isinstance(value, str):
                                        value = value.strip('[]').split(',')
                                    arguments[param_name] = [int(x.strip()) for x in value]
                                else:
                                    arguments[param_name] = str(value)
                            
                            # print(f"\nDEBUG: Final arguments: {arguments}")
                            # print(f"\nDEBUG: Calling tool {func_name}")
                            console.print(Panel(f"Calling tool {func_name} with {arguments} parameters", title="Calling tool", title_align="center", border_style="red"))
                            
                            result = await session.call_tool(func_name, arguments=arguments)
                            # print(f"\nDEBUG: Raw result: {result}")
                            
                            if hasattr(result, 'content'):
                                if isinstance(result.content, list):
                                    iteration_result = [
                                        item.text if hasattr(item, 'text') else str(item)
                                        for item in result.content
                                    ]
                                else:
                                    iteration_result = str(result.content)
                            else:
                                print(f"DEBUG: Result has no content attribute")
                                iteration_result = str(result)
                            
                            if isinstance(iteration_result, list):
                                result_str = f"[{', '.join(iteration_result)}]"
                            else:
                                result_str = str(iteration_result)
                            
                            iteration_response.append(
                                f"In the {iteration + 1} iteration you called {func_name} with {arguments} parameters, "
                                f"and the function returned {result_str}."
                            )
                            last_response = iteration_result
                            console.print(Panel(f"Result: {result_str}", title="Last response", title_align="center", border_style="green"))
                            if 'appointment_id' in result_str:
                                return result_str

                        except Exception as e:
                            return f"Error: {str(e)}"

                    elif response_text.startswith("FINAL_ANSWER:"):
                        final_response = response_text.replace("FINAL_ANSWER:", "").replace("[", "").replace("]", "").strip()
                        break
                        
                    # elif response_text.startswith("ADDITIONAL_INFO:"):
                    #     # For ADDITIONAL_INFO, just return the response text after stripping the prefix
                    #     final_response = response_text.replace("ADDITIONAL_INFO:", "").strip()
                    #     break

                    iteration += 1

                return final_response or "No response generated"

    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        reset_state()

async def main():
    """Main function for command line usage"""
    query = """
    Patient name is John Doe and he is 30 years old.
    """
    response = await process_query(query)
    print(f"Response: {response}")

if __name__ == "__main__":
    asyncio.run(main())
    