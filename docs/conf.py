project = "HydroOpsLM"
author = "HydroOpsLM contributors"
extensions = ["myst_nb"]
source_suffix = {".md": "myst-nb", ".ipynb": "myst-nb"}
root_doc = "index"
nb_execution_mode = "off"  # Render saved outputs; never run a notebook or model.
myst_enable_extensions = ["colon_fence", "deflist"]
myst_heading_anchors = 4
html_theme = "alabaster"
html_title = "HydroOpsLM documentation"
html_baseurl = "https://wenyuchiou.github.io/HydroOpsLM/"
# Sharing services need public absolute URLs, separate from the private repo.
html_context = {
    "site_url": html_baseurl,
    "social_image": html_baseurl + "_static/hydroopslm-social-preview.png",
    "social_description": (
        "Connect reservoir operation decisions, configurable information and "
        "language-model prompts to HydroCNHS hydrology and routing."
    ),
}
html_static_path = ["_static"]
html_css_files = ["manual.css"]
html_js_files = ["manual.js"]
html_favicon = "_static/logo-32.png"
html_theme_options = {"page_width": "1280px", "body_max_width": "960px",
                      "sidebar_width": "260px", "fixed_sidebar": True}
templates_path = ["_templates"]
html_sidebars = {"**": ["navigation.html"]}
exclude_patterns = ["_static/**", "_templates/**", "_notebook_downloads/**", "_case_downloads/**", "_hydrology_downloads/**"]
