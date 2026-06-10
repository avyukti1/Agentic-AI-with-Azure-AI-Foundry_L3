# Agentic AI with Azure AI Foundry (L3) - Mini Project 6

## Build Reasoning Agent using ReAct Framework

---

## Project Overview

This project demonstrates a **Reasoning Agent built using the ReAct (Reasoning + Acting) framework**, a core approach used in modern Agentic AI systems.

The system enables an AI agent to:

- Reason about a user query
- Decide on required actions
- Use tools dynamically
- Generate structured final responses

This project simulates how intelligent agents perform step-by-step reasoning before producing an output.

---

## Objective

The main objective of this project is to:

- Implement a reasoning-based AI agent using ReAct methodology
- Combine reasoning and tool execution in a single workflow
- Demonstrate structured decision-making in AI systems
- Build an extensible agentic reasoning framework
- Understand tool-augmented LLM behavior

---

## Key Features

- ReAct-based reasoning workflow
- Tool usage integration
- Step-by-step reasoning and action cycles
- Structured output generation
- Modular agent architecture
- Extensible tool system

---

## Project Structure
Mini_Project6/
│
├── app.py
│ Main application entry point
│
├── tools.py
│ External tools used by the agent
│
├── structured_response_demo.py
│ Demonstration of structured outputs
│
├── requirements.txt
│ Project dependencies
│
├── APPLICATION_LOGIC.md
│ Logic and workflow explanation for ReAct agent
│
├── pycache/
│ Python compiled cache files (auto-generated)
│
└── Build reasoning agent using ReAct.zip
Project archive / packaged source code


---

## How It Works (ReAct Framework)

The agent follows a structured loop:

### 1. Thought (Reasoning Phase)
- The agent analyzes the user query
- Breaks down the problem logically

### 2. Action (Tool Usage Phase)
- The agent selects appropriate tools
- Executes required operations

### 3. Observation
- The agent receives tool output
- Evaluates results

### 4. Final Answer
- The agent combines reasoning + observations
- Produces structured response

---

## Example Flow

User Query:
"What is the capital of a country and its population?"

Flow:
1. Agent identifies required knowledge
2. Selects tools for data retrieval
3. Executes tool calls
4. Observes results
5. Produces final structured answer

---

## Core Modules

### 1. Reasoning Engine (app.py)
- Handles ReAct loop execution
- Controls reasoning + action flow

---

### 2. Tools Module (tools.py)
- Provides external functions for the agent
- Enables data retrieval and processing

---

### 3. Structured Response Module
- Formats final outputs
- Ensures consistent response structure

---

## AI Concepts Used

### 1. ReAct Framework
- Combines reasoning and acting in AI systems
- Enables step-by-step decision making

### 2. Agentic AI
- Autonomous decision-making agent
- Tool-augmented intelligence

### 3. Tool-Augmented LLMs
- External function usage
- Dynamic tool selection

### 4. Structured Reasoning
- Chain-of-thought style reasoning
- Controlled output generation

---

## Technology Stack

- Python
- ReAct agent framework
- Tool-based execution system
- Prompt engineering
- Agentic AI design principles

---

## Learning Outcomes

After completing this project, you will understand:

- How ReAct agents function internally
- How reasoning and action are combined in AI systems
- How tools extend LLM capabilities
- How structured reasoning improves AI reliability
- How Agentic AI systems are designed

---

## Future Enhancements

- Integration with real LLM APIs (Azure OpenAI / GPT models)
- Advanced tool registry system
- Memory-enabled reasoning agents
- Multi-agent ReAct collaboration
- Deployment as API service
- UI-based interactive agent interface

---

## Project Type

- Mini Project
- Reasoning Agent Implementation
- ReAct Framework Simulation
- Agentic AI Architecture Prototype

---

## License

For educational and training purposes only.
