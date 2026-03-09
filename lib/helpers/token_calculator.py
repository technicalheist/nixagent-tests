import json
import os

MODEL_COSTS = {
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "qwen/qwen3.5-flash-02-23": {"input": 0.10, "output": 0.40},
    "qwen/qwen3.5-plus-02-15": {"input": 0.10, "output": 0.40}, # Temporary fallback price based on flash
    "google/gemini-3.1-flash-lite-preview": {"input": 0.25, "output": 1.50},
    "google/gemini-3-flash-preview": {"input": 0.50, "output": 3.0},
    "minimax/minimax-m2.5": {"input": 0.295, "output": 1.20},
    "moonshotai/kimi-k2.5": {"input": 0.45, "output": 2.20},
    "google/gemini-3.1-pro-preview": {"input": 2.0, "output": 12.0},
    "default": {"input": 0.0, "output": 0.0}
}

global_token_report = {
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "total_cost": 0.0,
    "agents": {}
}

def estimate_tokens(text: str, model: str) -> int:
    try:
        import tiktoken
        try:
            encoding = tiktoken.encoding_for_model(model)
        except Exception:
            encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except ImportError:
        # Fallback heuristic if tiktoken isn't installed
        return len(str(text)) // 4

def update_agent_usage(agent_name: str, model: str, in_tokens: int, out_tokens: int):
    if model not in MODEL_COSTS:
        print(f"\n⚠️ WARNING: Model '{model}' not found in MODEL_COSTS. Defaulting to $0.00.")
    costs = MODEL_COSTS.get(model, MODEL_COSTS["default"])
    cost = (in_tokens / 1_000_000) * costs["input"] + (out_tokens / 1_000_000) * costs["output"]
    
    if agent_name not in global_token_report["agents"]:
        global_token_report["agents"][agent_name] = {
            "model": model,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost": 0.0
        }
        
    global_token_report["agents"][agent_name]["input_tokens"] += in_tokens
    global_token_report["agents"][agent_name]["output_tokens"] += out_tokens
    global_token_report["agents"][agent_name]["cost"] += cost
    
    global_token_report["total_input_tokens"] += in_tokens
    global_token_report["total_output_tokens"] += out_tokens
    global_token_report["total_cost"] += cost

def with_token_calculator(agent):
    """
    Wraps an agent's run method to transparently calculate token usage in the background.
    """
    original_run = agent.run
    
    def wrapped_run(*args, **kwargs):
        start_idx = len(agent.messages)
        response = original_run(*args, **kwargs)
        end_idx = len(agent.messages)
        
        model = getattr(agent, "model", "default")
        if not model:
            model = "default"
            
        in_tokens = 0
        out_tokens = 0
        
        # Calculate tokens for any new assistant messages generated in this run
        for i in range(start_idx, end_idx):
            msg = agent.messages[i]
            if msg.get("role") == "assistant":
                prior_messages = agent.messages[:i]
                input_text = json.dumps(prior_messages)
                if hasattr(agent, "tool_defs") and agent.tool_defs:
                    input_text += json.dumps(agent.tool_defs)
                    
                in_tokens += estimate_tokens(input_text, model)
                out_tokens += estimate_tokens(json.dumps(msg), model)
                
        update_agent_usage(agent.name, model, in_tokens, out_tokens)
        return response
        
    agent.run = wrapped_run
    return agent

def get_token_report() -> str:
    report = [
        "",
        "📊 Token Usage & Cost Report 📊",
        "-" * 40
    ]
    for name, data in global_token_report["agents"].items():
        report.append(f"Agent: {name} ({data['model']})")
        report.append(f"  Input Tokens:  {data['input_tokens']}")
        report.append(f"  Output Tokens: {data['output_tokens']}")
        report.append(f"  Cost:          ${data['cost']:.4f}")
        report.append("-" * 20)
    
    report.append("TOTALS")
    report.append(f"  Input Tokens:  {global_token_report['total_input_tokens']}")
    report.append(f"  Output Tokens: {global_token_report['total_output_tokens']}")
    report.append(f"  Total Cost:    ${global_token_report['total_cost']:.4f}")
    report.append("=" * 40)
    return "\n".join(report)
