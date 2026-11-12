# File Reader skill entry point
def run(function_name, params, ctx):
    if function_name == "read_file":
        path = params.get("path", "")
        return ctx.files.read(path)
    return {"ok": False, "error": f"Unknown function: {function_name}"}
