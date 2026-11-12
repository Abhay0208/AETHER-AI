# File Writer skill entry point
def run(function_name, params, ctx):
    if function_name == "write_file":
        path = params.get("path", "")
        content = params.get("content", "")
        return ctx.files.write(path, content)
    return {"ok": False, "error": f"Unknown function: {function_name}"}
