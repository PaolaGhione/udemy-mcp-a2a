import json
from agent_framework import AIAgent, MCPGatewayClient

# 1. Load the skill definition
with open("sim_activation_skill.json", "r") as file:
    skill_definition = json.load(file)

# 2. Connect to your central MCP Gateway
gateway = MCPGatewayClient(url="https://gateway.internal.enterprise")

# 3. Initialize the agent with the gateway and the skill
agent = AIAgent(
    name="TelecomServiceAgent",
    model="claude-3-5-sonnet",
    mcp_gateway=gateway
)

# 4. Register the skill into the agent's capability library
agent.register_skill(skill_definition)