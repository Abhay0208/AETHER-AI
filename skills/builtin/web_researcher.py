# Web Researcher skill entry point
def run(function_name, params, ctx):
    if function_name == "research":
        topic = params.get("topic", "")
        model = params.get("model")
        if not model:
            return {"ok": False, "error": "model is required for research"}
        messages = [
            {"role": "system",
             "content": "You are a research assistant. Research the given topic thoroughly and provide a structured summary with key findings."},
            {"role": "user",
             "content": f"Research this topic and provide a comprehensive summary:\n\n{topic}"},
        ]
        return ctx.model.chat(messages, model)
    return {"ok": False, "error": f"Unknown function: {function_name}"}
