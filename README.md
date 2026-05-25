# OmniAgent MVP

**A minimal AI Agent framework in ~2,300 lines of Python. Build terminal-based agents like Hermes and Claude Code with complete tool calling, error recovery, and multi-model support.**

[中文文档](README_CN.md)

---

## 🎯 Built for Developers

OmniAgent MVP is an AI Agent framework designed specifically for developers, enabling you to quickly build and customize your own intelligent assistants.

### Core Capabilities

- **Programming Agent** - Code search, file editing, project analysis
- **Desktop Agent** - File operations, system commands, task automation
- **Tool Extension** - Simple tool registration mechanism for easy custom functionality

### Features

- ✅ **Multi-Model Support** - OpenAI, Anthropic, local models (Ollama, LM Studio, vLLM)
- ✅ **Complete Agent Loop** - Task decomposition, tool calling, result integration
- ✅ **12 Built-in Tools** - shell, read_file, write_file, edit_file, grep, glob + 6 process management tools
- ✅ **Background Process Support** - Run long tasks, interactive commands, development servers
- ✅ **Error Recovery** - Intelligent retry mechanism, inspired by Hermes design
- ✅ **Safety Guards** - Dangerous command detection, path safety checks
- ✅ **Streaming Output** - Real-time AI response display

---

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/keyxh/omniagent-mvp.git
cd omniagent-mvp
pip install -r requirements.txt
```

### Command Line Arguments

```bash
python cli.py [OPTIONS] [TASK]

Options:
  --model         Model name (default: gpt-4)
  --base-url      API base URL (optional, for local models)
  --api-key       API key (optional, reads from environment by default)
  --provider      LLM provider (openai/anthropic, default: openai)
  --max-iterations Maximum iterations (default: 50)
  --max-tokens    Maximum context length (default: 100k)
  TASK            Task to execute (optional, enters interactive mode if not provided)
```

### Usage Examples

```bash
# Using OpenAI
python cli.py --model gpt-4 "List all Python files in current directory"

# Using Anthropic
python cli.py --provider anthropic --model claude-3-opus-20240229 "Analyze code structure"

# Using local model
python cli.py --model llama2 --base-url http://localhost:11434/v1 --api-key not-need "Hello"

# Interactive mode
python cli.py
```

---

## 💡 Use Cases

### Programming Agent

```bash
# Code search
python cli.py "Search all Python files containing TODO"

# Code analysis
python cli.py "Analyze the main functionality of engine.py"

# Code editing
python cli.py "Add logging functionality to cli.py"
```

### Desktop Agent

```bash
# File management
python cli.py "Organize current directory, move all images to images folder"

# System operations
python cli.py "Check system disk usage"

# Automation tasks
python cli.py "Backup all .py files to backup directory"
```

---

## 🔧 Custom Tools

Adding custom tools is simple:

```python
from engine import get_registry

registry = get_registry()

def my_tool(args, working_dir):
    # Your tool logic
    return {"result": "success"}

registry.register(
    name="my_tool",
    handler=my_tool,
    description="My custom tool",
    parameters={
        "type": "object",
        "properties": {
            "param": {"type": "string"}
        }
    }
)
```

---

## 📊 Project Structure

```
omniagent-mvp/
├── omni/              # Core engine (~1,300 lines)
│   ├── engine.py      # Agent main loop
│   ├── client.py      # Multi-model client
│   ├── brain.py       # Prompt generation
│   ├── memory.py      # Context management (Hermes-style)
│   ├── shield.py      # Safety checks
│   └── recovery.py    # Error recovery
├── engine/            # Tool system (~1,000 lines)
│   ├── registry.py    # Tool registry
│   ├── filesystem.py  # File operations
│   ├── search.py      # Search tools
│   ├── shell.py       # Shell tool
│   └── process_manager.py  # Background process management
├── cli.py             # CLI entry point
└── requirements.txt   # Dependencies (only 5 packages)
```

**Total: ~2,300 lines of code**

---

## 🎓 Why Choose OmniAgent MVP?

- **Learning Friendly** - Clean and concise code, each file under 300 lines
- **Feature Complete** - Includes production-grade Agent core capabilities
- **Easy to Extend** - Simple tool registration mechanism
- **Ready to Use** - Supports mainstream LLMs and local models

---

## 🏗️ Architecture Highlights

### Hermes-Style Context Compression

OmniAgent MVP implements Hermes v3 compression strategy:

**4-Phase Algorithm:**
1. **Phase 1: Zero-cost preprocessing** - MD5 deduplication + Smart Collapse
2. **Phase 2: Boundary protection** - Protect head and tail messages
3. **Phase 3: Structured summary** - Action-log style summary
4. **Phase 4: Tool call cleanup** - Remove orphaned tool calls

**Benefits:**
- ✅ Prevents context overflow
- ✅ Maintains stable inference speed
- ✅ Preserves important information
- ✅ Supports long conversations

---

## 📄 License

MIT License

---

## 🙏 Acknowledgments

This project is inspired by the design philosophy of the following open-source projects:

- [Hermes Agent](https://github.com/NousResearch/hermes-agent) - Context compression strategy and error recovery mechanism
- [Claude Code](https://claude.ai/code) - Agentic loop design

All code is original implementation, following MIT License.

---

## 🌟 Star History

If this project helps you, please give it a Star ⭐️!

---

## 🚧 Roadmap

- **Full Version Agent** - Complete version based on backend architecture, coming soon with more advanced features
- **Pseudo-terminal Mode** - Temporarily shelved due to technical challenges with streaming and tool calling, will be supported in the future

---

## 🤝 Contributing

Issues and Pull Requests are welcome!

---

**Built with ❤️ for developers**
