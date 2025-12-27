import os
import sys
import time
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Add backend directory to path for imports when run directly
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from agent.memory import MemoryManager, MemoryItem
from agent.perception import extract_perception
from agent.decision import generate_plan
from agent.action import execute_tool
from agent.logger import logger
import pdb
import json



max_steps = 3

async def run_agent(query, top_k: int = 5):
    """
    Agent to handle the requests
    
    Args:
        query: The user query to process
        top_k: Number of top results to return (default: 5)
    
    Returns:
        List of results from the agent execution
    """
    logger.info("Agent starting...")
    results = []
    try:
        logger.debug(f"Current working directory: {os.getcwd()}")
        logger.info(f"Establishing connection to MCP server...")
        # Get the backend directory (parent of agent directory)
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        action_path = os.path.join(backend_dir, "agent", "mcp_server_1.py")
        server_params = StdioServerParameters(
            command="python",
            args=[action_path],
            cwd=backend_dir
        )
        async with stdio_client(server_params) as (read, write):
            logger.info("Connection established, creating session...")
            async with ClientSession(read, write) as session:
                logger.info("Session created, initializing...")
                await session.initialize()

                # Get available tools
                logger.info("Requesting tool list...")
                tools_result = await session.list_tools()
                tools = tools_result.tools
                logger.info(f"Successfully retrieved {len(tools)} tools")
                tool_descriptions = "\n".join(
                                f"- {tool.name}: {getattr(tool, 'description', 'No description')}" 
                                for tool in tools
                            )

                memory = MemoryManager()
                session_id = f"session-{int(time.time())}"
                user_query = query
                step = 0

                while step < max_steps:
                    logger.info(f"Step {step + 1} started")
                    # pdb.set_trace()

                    perception = extract_perception(user_query)
                    logger.info(f"Perception - Intent: {perception.intent}, Tool hint: {perception.tool_hint}")

                    retrieved = memory.retrieve(query=user_query, top_k=3, session_filter=session_id)
                    logger.info(f"Memory - Retrieved {len(retrieved)} relevant memories")

                    plan = generate_plan(perception, retrieved, tool_descriptions=tool_descriptions)
                    logger.info(f"Plan - Plan generated: {plan}")

                    if plan.startswith("FINAL_ANSWER:"):
                        logger.info(f"Agent - ✅ FINAL RESULT: {plan}")
                        # Extract the answer from FINAL_ANSWER format
                        answer = plan.replace("FINAL_ANSWER:", "").strip()
                        # If the answer contains results, try to parse them
                        if isinstance(answer, str) and answer.startswith("["):
                            try:
                                import ast
                                results = ast.literal_eval(answer)
                            except:
                                results = [{"answer": answer}]
                        else:
                            results = [{"answer": answer}]
                        logger.info(f"Agent - STRIPPER FINAL ANSWER: {results}")
                        if(isinstance(results[0], str)):
                             results = [json.loads(val) for val in results] # if the list elements are str, convert them to json/dict
                        
                        break

                    try:
                        result = await execute_tool(session, tools, plan)
                        logger.info(f"Tool - {result.tool_name} returned: {result.result}")
                        if (isinstance(result.result, list) and all(isinstance(value, dict) for value in result.result)):
                            result.result = [json.dump(value) for value in result.result]
                            logger.info(f"Tool - {result.tool_name} result converted to string: {result.result}")
                        
                        # memory.add(MemoryItem(
                        #     text=f"Tool call: {result.tool_name} with {result.arguments}, got: {result.result}",
                        #     type="tool_output",
                        #     tool_name=result.tool_name,
                        #     user_query=user_query,
                        #     tags=[result.tool_name],
                        #     session_id=session_id
                        # ))
                        # logger.info(f"Memory - Added the tool execution result to memory (as session memory item)")

                        # If the result is a list (like search results), add them to results
                        if isinstance(result.result, list):
                            results.extend(result.result[:top_k])
                        elif result.tool_name == "search_browser_history":
                            # Handle search results specifically
                            if isinstance(result.result, list):
                                results = result.result[:top_k]
                            else:
                                results = [result.result]

                        user_query = f"Original task: {query}\nPrevious output: {result.result}\nWhat should I do next?"

                    except Exception as e:
                        logger.error(f"Tool execution failed: {e}")
                        break

                    step += 1

    except Exception as e:
        logger.error(f"Overall error: {str(e)}", exc_info=True)
        raise

    logger.info("Agent Session Completed!!!")
    return results if results else []