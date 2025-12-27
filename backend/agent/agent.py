import os
import time
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from agent.memory import MemoryManager, MemoryItem
from agent.perception import extract_perception
from agent.decision import generate_plan
from agent.action import execute_tool
from agent.logger import logger



max_steps = 3

async def agent():
    """
    Agent to handle the requests
    """
    logger.info("Agent starting...")
    try:
        logger.debug(f"Current working directory: {os.getcwd()}")
        logger.info(f"Establishing connection to MCP server...")
        # Get the backend directory (parent of agent directory)
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        action_path = os.path.join(backend_dir, "agent", "action.py")
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

                # TODO
                query = """Search the user input query '' to find the results"""

                memory = MemoryManager()
                session_id = f"session-{int(time.time())}"
                user_query = query

                while step < max_steps:
                    logger.info(f"Step {step + 1} started")

                    perception = extract_perception(user_query)
                    logger.info(f"Perception - Intent: {perception.intent}, Tool hint: {perception.tool_hint}")

                    retrieved = memory.retrieve(query=user_query, top_k=3, session_filter=session_id)
                    logger.info(f"Memory - Retrieved {len(retrieved)} relevant memories")

                    plan = generate_plan(perception, retrieved, tool_descriptions=tool_descriptions)
                    logger.info(f"Plan - Plan generated: {plan}")

                    if plan.startswith("FINAL_ANSWER:"):
                        logger.info(f"Agent - ✅ FINAL RESULT: {plan}")
                        break

                    try:
                        result = await execute_tool(session, tools, plan)
                        logger.info(f"Tool - {result.tool_name} returned: {result.result}")
                        # pdb.set_trace()
                        memory.add(MemoryItem(
                            text=f"Tool call: {result.tool_name} with {result.arguments}, got: {result.result}",
                            type="tool_output",
                            tool_name=result.tool_name,
                            user_query=user_query,
                            tags=[result.tool_name],
                            session_id=session_id
                        ))

                        user_query = f"Original task: {query}\nPrevious output: {result.result}\nWhat should I do next?"

                    except Exception as e:
                        logger.error(f"Tool execution failed: {e}")
                        break

                    step += 1

    except Exception as e:
        logger.error(f"Overall error: {str(e)}", exc_info=True)
        raise

    logger.info("Agent Session Completed!!!")