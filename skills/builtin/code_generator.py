# Code Generator skill entry point
def run(function_name, params, ctx):
    if function_name == "generate":
        task = params.get("task", "")
        language = params.get("language", "python")
        model = params.get("model")
        if not model:
            return {"ok": False, "error": "model is required for code generation"}
        messages = [
            {"role": "system",
             "content": f"You are an expert {language} programmer. Generate clean, well-documented code."},
            {"role": "user",
             "content": f"Write {language} code to accomplish the following task:\n\n{task}\n\nReturn only the code, with brief comments."},
        ]
        return ctx.model.chat(messages, model)
    return {"ok": False, "error": f"Unknown function: {function_name}"}
