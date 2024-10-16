# Agora - A Scalable Communication Protocol for Networks of LLMs
[Paper](.) | [Website](https://agoraprotocol.org) | [Discord](https://discord.gg/MXmfhwQ4FB) | [Mailing List](https://forms.gle/KeCMveoRGx2S3i5CA)

Agora is a simple cross-platform protocol that allows heterogeneous LLMs to communicate efficienly with each other.
This is achieved through the power of **negotiation**.

In particular, Agora agents operate as follows:
1. For rare communications, they use LLMs to talk with each other in natural language
2. For frequent communications, they use LLMs to negotiate a protocol for communication, usually involving structured data (e.g. JSON)
3. Once a protocol is finalized, they use LLMs to implement _routines_, simple scripts (e.g. in Python) that send or receive data
4. Future communications are handled using the routines, which means that LLMs aren't required anymore

Since natural language is supported, very different agents that have never interacted before can communicate with each other, but once a common ground is established they just use routines, which are way more efficient. This enables agents to achieve both **efficiency** and **portability**.

## The Demo

This demo showcases a network of 100 agents interacting with each other. The agents have different LLMs (OpenAI GPT-4o, Llama 3 405b, Gemini 1.5 Pro) and different DB technologies (MongoDB, SQL), but they still complete complex, multi-agent tasks with way lower costs. In a picture:

<img src="./static/readme_comparison.png?raw=true">


## Running the Demo

1. `mv .env.template .env`
2. Add the corresponding fields to the `.env` file
3. `pip install -r requirements.txt`

## Contributing

We're building the next iteration of Agora, with more features for real-world use cases. If you're interested in contributing or simply want to stay updated about Agora, check out our [Discord](https://discord.gg/MXmfhwQ4FB) or subscribe to our [Mailing List](https://forms.gle/KeCMveoRGx2S3i5CA)