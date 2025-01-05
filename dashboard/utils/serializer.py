from dash.development.base_component import Component
from ..models_impact import models_impact_page
from ..community import community_blog_page
from ..events_and_publications import events_publications_page
import json

import plotly.io as pio

def serialize_dash_component(component):
    """
    Recursively serialize a Dash component into a JSON-compatible dictionary.
    Handles Dash components, lists, dictionaries, and primitive types.
    """
    if isinstance(component, Component):
        props = {}
        for prop in component._prop_names:
            value = getattr(component, prop, None)
            if prop == "figure" and value is not None:
                # plotly handling
                props[prop] = json.loads(pio.to_json(value))  # figures to JSON-compatible dict
            elif value is not None:
                props[prop] = serialize_dash_component(value)  # serialize other properties

        return {
            "type": component.__class__.__name__,
            "props": props
        }
    elif isinstance(component, list):
        # serialize lists of components
        return [serialize_dash_component(c) for c in component]
    elif isinstance(component, dict):
        # serialize dictionaries of components
        return {k: serialize_dash_component(v) for k, v in component.items()}
    else:
        # serialize primitive types (strings, numbers, None)
        return component
    
def save_layout_to_json(page_function, filename):
    serialized_layout = serialize_dash_component(page_function())

    with open(filename, "w") as f:
        json.dump(serialized_layout, f, indent=4)

# generate JSON layouts into assets folder
save_layout_to_json(models_impact_page, "dashboard/assets/models_impact.json")
save_layout_to_json(community_blog_page, "dashboard/assets/community_blog.json")
save_layout_to_json(events_publications_page, "dashboard/assets/events_publications.json")