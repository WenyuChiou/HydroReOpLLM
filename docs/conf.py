project = "HydroReOpLLM"
author = "HydroReOpLLM contributors"
extensions = ["myst_nb"]
source_suffix = {".md": "myst-nb", ".ipynb": "myst-nb"}
root_doc = "index"
nb_execution_mode = "off"  # Render saved outputs; never run a notebook or model.
myst_enable_extensions = ["colon_fence", "deflist", "dollarmath"]
myst_heading_anchors = 4
html_theme = "alabaster"
html_title = "Hydrological Simulation with Large Language Model Reservoir Operations"
html_short_title = project
html_baseurl = "https://wenyuchiou.github.io/HydroReOpLLM/"
# Sharing services need public absolute URLs, separate from the private repo.
html_context = {
    "site_url": html_baseurl,
    "social_image": html_baseurl + "_static/hydroopslm-social-preview.png",
    "social_description": (
        "Hydrological Simulation with Large Language Model Reservoir Operations. "
        "Built on HydroCNHS."
    ),
}
html_static_path = ["_static"]
html_css_files = ["manual.css", "reading.css"]
html_js_files = ["manual.js", "prompt-review.js", "navigation.js"]
html_favicon = "_static/logo-32.png"
html_theme_options = {"page_width": "1280px", "body_max_width": "960px",
                      "sidebar_width": "260px", "fixed_sidebar": True}
templates_path = ["_templates"]
html_sidebars = {"**": ["navigation.html"]}
exclude_patterns = ["_static/**", "_templates/**", "_notebook_downloads/**", "_case_downloads/**", "_hydrology_downloads/**", "_figure_downloads/**", "_config_downloads/**", "_completed_downloads/**", "_tutorial_downloads/**", "_template_downloads/**", "examples/fe_walter/knowledge/**"]
exclude_patterns.append("_downstream_downloads/**")
exclude_patterns.append("_daily_downloads/**")
exclude_patterns.append("tutorials/downstream_validation.ipynb")  # Download the walkthrough; keep manual pages concise.
