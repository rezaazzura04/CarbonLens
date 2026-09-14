"""CarbonLens — Typography constants."""

# Font families — Inter is used throughout the entire application (brand
# headings, body text, tables, numerical data, forms, charts). FONT_BRAND
# is kept as a distinct name for call-site clarity (e.g. "this is a page
# title, not body copy") but intentionally points to the same Inter family,
# not a separate typeface.
FONT_BODY  = "'Inter', -apple-system, sans-serif"
FONT_BRAND = FONT_BODY

# Font sizes (px)
SIZE_XS    = "9px"
SIZE_SM    = "10px"
SIZE_BASE  = "12px"
SIZE_MD    = "14px"
SIZE_LG    = "16px"
SIZE_XL    = "20px"
SIZE_2XL   = "24px"
SIZE_3XL   = "28px"

# Font weights
WEIGHT_NORMAL  = "400"
WEIGHT_MEDIUM  = "500"
WEIGHT_SEMIBOLD= "600"
WEIGHT_BOLD    = "700"
WEIGHT_BLACK   = "800"

# Line heights
LEADING_TIGHT  = "1.2"
LEADING_NORMAL = "1.5"
LEADING_LOOSE  = "1.8"

# Letter spacing
TRACKING_WIDE  = "0.8px"
TRACKING_WIDER = "1.2px"

# Common style snippets
LABEL_STYLE = (
    f"font-family:{FONT_BODY};font-size:{SIZE_XS};font-weight:{WEIGHT_BOLD};"
    f"text-transform:uppercase;letter-spacing:{TRACKING_WIDE};color:var(--text-muted);"
)
TITLE_STYLE = (
    f"font-family:{FONT_BRAND};font-size:{SIZE_XL};font-weight:{WEIGHT_BLACK};"
    f"color:var(--text-primary);letter-spacing:-0.5px;"
)
CAPTION_STYLE = (
    f"font-family:{FONT_BODY};font-size:{SIZE_SM};color:var(--text-muted);"
)
