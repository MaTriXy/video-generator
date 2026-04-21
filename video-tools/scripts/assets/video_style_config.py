"""Video style configuration for icon library prioritization."""


DEFAULT_STYLE = {
    "primary_libraries": [
        "openmoji", "twemoji", "unjs", "noto", "emojione", "emojione-v1",
        "fxemoji", "streamline-emojis", "vscode-icons", "material-icon-theme",
        "fluent-emoji-flat", "fluent-emoji-high-contrast",
        "emojione-monotone"
    ],
    "secondary_libraries": [
        "catppuccin", "streamline-ultimate-color"
    ]
}


COMPANY_LOGO_LIBRARIES = ["logos"]


VIDEO_STYLE_CONFIG = {
    "default": "minimal-blue",
    "styles": {
        "what-if": DEFAULT_STYLE,
        "minimal-blue": DEFAULT_STYLE,
        "4g5g": DEFAULT_STYLE,
        "vox": DEFAULT_STYLE,
        "typography-apple": DEFAULT_STYLE,
    }
}
