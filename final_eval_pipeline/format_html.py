def format_text_as_html(content: str) -> str:
    """
    Converts Markdown-style text into simple structured HTML.
    - Lines starting with 'Overview:' -> <h2>
    - Lines starting with '## ' -> <h2>
    - Lines starting with '### ' -> <h3>
    - Lines with indentation (4 spaces) -> <pre> to preserve formatting
    - Other lines -> <p>
    """
    html_lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("Overview:"):
            html_lines.append(f"<h2>{stripped}</h2>")
        elif stripped.startswith("## "):
            html_lines.append(f"<h2>{stripped[3:]}</h2>")
        elif stripped.startswith("### "):
            html_lines.append(f"<h3>{stripped[4:]}</h3>")
        elif line.startswith("    "):  # preserve indented blocks
            # remove default gray outline, subtle background, padding
            html_lines.append(f"<pre class='code-block'>{line[4:]}</pre>")
        elif stripped:
            html_lines.append(f"<p>{stripped}</p>")
        else:
            html_lines.append("<br>")
    return "\n".join(html_lines)

def create_html_file(content: str, filename: str = "output.html") -> None:
    """
    Creates a clean HTML file from the structured content.
    """
    html_content = format_text_as_html(content)
    html_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>SET Evaluation Report</title>
<style>
body {{
    font-family: Arial, sans-serif;
    background-color: #ffffff;
    margin: 0;
    padding: 0;
    display: flex;
    justify-content: center;  /* centers the container horizontally */
}}
.container {{
    max-width: 2600px;
    padding: 40px;
    box-sizing: border-box;
}}
h2 {{ color: #2c3e50; margin-top: 1.5em; }}
h3 {{ color: #34495e; margin-top: 1em; }}
p {{ line-height: 1.6; margin: 0.5em 0; }}
pre.code-block {{
    font-family: 'Courier New', monospace;
    background-color: #f9f9f9; /* subtle background */
    padding: 10px 15px;
    border-radius: 4px;
    overflow-x: auto;
    margin: 10px 0;
}}
</style>
</head>
<body>
<div class="container">
{html_content}
</div>
</body>
</html>"""

    with open(filename, "w", encoding="utf-8") as file:
        file.write(html_page)
