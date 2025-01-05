import json
import os
from plotly.io import write_image

# directory containing JSON files and images
json_dir = "dashboard/assets"
output_dir = "dashboard/exported_pages"
graphs_dir = "graphs"  # export graph images here
graphs_path = os.path.join(output_dir, graphs_dir)

# output dir checker
os.makedirs(output_dir, exist_ok=True)
os.makedirs(graphs_path, exist_ok=True)

def style_dict_to_str(style_dict):
    """
    Convert style dictionary to valid CSS inline style string
    """
    if not style_dict:
        return ""
    return "; ".join(f"{k.replace('_', '-')}: {v}" for k, v in style_dict.items())

def extract_graph_dimensions(style):
    """
    Extract width/ height from the style dictionary if exists
    """
    if not style or not isinstance(style, dict):
        return "width: 100%; height: auto;"  # default styling

    width = style.get("width", "100%")
    height = style.get("height", "auto")
    return f"width: {width}; height: {height};"

# sidebar navigation template
def generate_sidebar():
    """
    Generate a sidebar navigation menu with links for the three pages.
    """
    return f"""
    <div style="padding: 20px; width: 250px; background-color: #f8f9fa; position: fixed; height: 100%; box-shadow: 2px 0px 5px rgba(0,0,0,0.1);">
        <div style="text-align: center;">
            <a href="/">
                <img src="../assets/logo.png" style="width: 200px; margin-bottom: 20px;" alt="Ersilia Logo">
            </a>
        </div>
        <div style="padding: 10px;">
            <div style="display: flex; align-items: center; margin-bottom: 10px; padding: 5px; border-radius: 40px;">
                <img src="../assets/icon_impact.png" style="width: 20px; margin-right: 10px;" alt="Icon for Models' Impact">
                <a href="models_impact.html" style="color: black; font-weight: normal; text-decoration: none; font-size: 14px;">
                    Models' Impact
                </a>
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 10px; padding: 5px; border-radius: 40px;">
                <img src="../assets/icon_community.png" style="width: 20px; margin-right: 10px;" alt="Icon for Community & Blog">
                <a href="community_blog.html" style="color: black; font-weight: normal; text-decoration: none; font-size: 14px;">
                    Community & Blog
                </a>
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 10px; padding: 5px; border-radius: 40px;">
                <img src="../assets/icon_publication.png" style="width: 20px; margin-right: 10px;" alt="Icon for Events & Publications">
                <a href="events_publications.html" style="color: black; font-weight: normal; text-decoration: none; font-size: 14px;">
                    Events & Publications
                </a>
            </div>
        </div>
    </div>
    """

# recursively convert JSON layout to HTML
def json_to_html(component, page_name, graph_count):
    if isinstance(component, str):  # keep text
        return component
    if isinstance(component, list):  # list of components
        return "".join(json_to_html(c, page_name, graph_count) for c in component)
    if isinstance(component, dict):  # components object
        tag = component.get("type", "").lower()  # Use the "type" as the HTML tag (Div = div)
        props = component.get("props", {})
        children = props.pop("children", None)

        # handle graphs/ figures dcc.Graph (replace with an <img> tag)
        if tag == "graph" and "figure" in props:
            graph_count[0] += 1
            graph_filename = f"{page_name}_graph_{graph_count[0]}.png"
            graph_filepath = os.path.join(graphs_path, graph_filename)
            figure = props["figure"]

            # export the figure to an image file 
            try:
                write_image(figure, graph_filepath, format="png", width=800, height=600)
            except Exception as e:
                print(f"Error exporting graph to {graph_filepath}: {e}")
                return f'<div style="color: red;">Error rendering graph</div>'

            # extract original dimensions from style (from json)
            graph_style = props.get("style", {})
            img_style = extract_graph_dimensions(graph_style)

            # get graph title for alt text
            graph_title = figure.get("layout", {}).get("title", {}).get("text", "Graph")

            # return an <img> tag referencing the exported image with original dimensions
            return f'<img src="{graphs_dir}/{graph_filename}" style="{img_style} margin: 10px 0;" alt="Graph: {graph_title}">'

        # convert everything to HTML attributes
        attributes = []
        for key, value in props.items():
            if key == "style" and isinstance(value, dict):
                # style dictionary to inline CSS
                attributes.append(f'style="{style_dict_to_str(value)}"')
            else:
                attributes.append(f'{key.replace("_", "-")}="{value}"')
        attributes_str = " ".join(attributes)

        # render children
        rendered_children = json_to_html(children, page_name, graph_count)

        return f"<{tag} {attributes_str}>{rendered_children}</{tag}>"
    return ""  # fallback for unsupported types

# for each JSON file into HTML (loop)
pages = {
    "models_impact": "Models' Impact",
    "community_blog": "Community & Blog",
    "events_publications": "Events & Publications"
}

for filename, icon_name in pages.items():
    json_file = f"{filename}.json"
    if json_file in os.listdir(json_dir):
        with open(os.path.join(json_dir, json_file), "r") as f:
            try:
                layout = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Error decoding {json_file}: {e}")
                continue

        # generate HTML from JSON layout
        graph_count = [0]  # reset graph counter for each page (to keep consistent)
        sidebar = generate_sidebar()
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{icon_name}</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; display: flex; }}
                img {{ max-width: 100%; }}
                div {{ margin-bottom: 20px; }}
                nav a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            {sidebar}
            <div style="margin-left: 300px; padding: 20px;">
                <h1 style="font-size: 24px; font-weight: bold;">{icon_name}</h1>
                {json_to_html(layout, filename, graph_count)}
            </div>
        </body>
        </html>
        """

        # save the HTML to a file
        output_html_file = os.path.join(output_dir, f"{filename}.html")
        with open(output_html_file, "w") as f:
            f.write(html_content)

        print(f"Generated HTML for {filename} at {output_html_file}")

print(f"Static HTML pages and graphs saved to {output_dir}")