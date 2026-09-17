# Basic Inventory Agent Loop AI

A simple AI-powered inventory management system built with **FastAPI**, **Groq/OpenAI-compatible tool calling**, and a manual **agent loop** in Python.

The system allows a store owner to interact with inventory using natural language while the AI agent decides which API tool to call.

## Features

- List current inventory
- Add new products
- Increase or decrease stock
- Detect low-stock products
- Persist inventory in `products.csv`
- Maintain conversation history during the session
- Log user, agent, and tool events in `conversation_log.csv`
- Use an LLM to decide which inventory action to perform

## Project Structure

```text
.
├── api/
│   ├── __init__.py
│   └── app.py
├── agent.py
├── products.csv
├── pyproject.toml
├── uv.lock
├── .python-version
├── .gitignore
└── README.md
```

## Requirements

- Python 3.14+
- `uv`
- Groq API key

## Installation

Install the dependencies:

```bash
uv sync
```

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_api_key_here
```

The `.env` file is ignored by Git and must never be committed.

## Run the API

Open one terminal and run:

```bash
uv run uvicorn api.app:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

## Run the Agent

Open a second terminal:

```bash
uv run python agent.py
```

Then interact with the inventory using natural language.

Example:

```text
Carla: How much Oat Milk do we have?

Agent: You currently have 70 liters of Oat Milk in stock.
```

Inventory update:

```text
Carla: We received 20 liters of Oat Milk today.

[tool] get_inventory -> {}
[tool] update_inventory -> {'product_id': 1, 'quantity_change': 20}

Agent: The inventory has been updated. Oat Milk now has 70 liters in stock.
```

Low-stock check:

```text
Carla: What products are running low?

[tool] get_low_stock_alerts -> {}

Agent: Vanilla Syrup is currently running low.
```

Create a product:

```text
Carla: Add a new product called Matcha Powder with 10 kg in stock and a low-stock threshold of 3 kg.
```

## API Endpoints

### List inventory

```http
GET /inventory
```

### Create a product

```http
POST /inventory
```

Example body:

```json
{
  "name": "Matcha Powder",
  "quantity": 10,
  "unit": "kg",
  "low_stock_threshold": 3
}
```

### Update inventory

```http
PATCH /inventory/{product_id}
```

Add stock:

```json
{
  "quantity_change": 20
}
```

Remove stock:

```json
{
  "quantity_change": -12
}
```

### Low-stock alerts

```http
GET /inventory/alerts
```

## Agent Loop

The agent implements the following loop manually:

```text
User input
    ↓
LLM receives messages and tool definitions
    ↓
LLM decides whether to call a tool
    ↓
Python executes the selected API tool
    ↓
Tool result is added back to the message history
    ↓
LLM evaluates the result
    ↓
Repeat if another tool is needed
    ↓
Final response
```

The agent keeps the complete message history in memory during each session.

## Conversation Log

Every agent-loop event is appended to:

```text
conversation_log.csv
```

The log contains:

```text
actor,message,tool_call,timestamp
```

Possible actors:

- `user`
- `agent`
- `tool`

The log is append-only and is not overwritten between sessions.

## Inventory Persistence

Inventory data is stored in:

```text
products.csv
```

Changes made through the agent or API remain available after restarting the application.