# Art-style catalog. Each entry is the LITERAL block injected into prompts —
# the "NOT a photograph" repetition is intentional, image models otherwise
# default to photorealistic interpretations of "5-year-old child", which is
# explicitly what we want to avoid.
ART_STYLES: dict[str, dict] = {
    "storybook": {
        "label": "Klasyczna ilustracja książkowa",
        "style_block": (
            "Warm children's book ILLUSTRATION (drawn and painted on paper — "
            "this is NOT a photograph, NOT photorealistic, NOT a real child). "
            "Soft painterly textures, hand-drawn feel, vibrant but not "
            "oversaturated palette. Professional children's book art."
        ),
    },
    "pixar": {
        "label": "Pixar / Disney 3D",
        "style_block": (
            "3D animated film STILL in Pixar/Disney style (rendered cartoon "
            "character — this is NOT a photograph, NOT photorealistic, NOT a "
            "real child). Stylized cartoon proportions, expressive large eyes, "
            "polished cinematic lighting, magical fairytale realism."
        ),
    },
    "watercolor": {
        "label": "Akwarela",
        "style_block": (
            "Watercolor PAINTING on textured paper (painted with watercolors — "
            "this is NOT a photograph, NOT photorealistic, NOT a real child). "
            "Delicate translucent washes, visible brush strokes, soft edges, "
            "gentle pastel palette."
        ),
    },
    "anime": {
        "label": "Anime / Studio Ghibli",
        "style_block": (
            "Hand-drawn anime ILLUSTRATION in Studio Ghibli / Miyazaki style "
            "(this is NOT a photograph, NOT photorealistic, NOT a real child). "
            "Cel-shaded character with expressive large eyes, painted "
            "backgrounds, warm magical atmosphere."
        ),
    },
    "flat": {
        "label": "Płaska wektorowa",
        "style_block": (
            "Flat 2D vector ILLUSTRATION with clean geometric shapes (this is "
            "NOT a photograph, NOT photorealistic, NOT a real child). Bold "
            "flat colors, minimal shading, simplified character design, modern "
            "children's book look."
        ),
    },
    "crayon": {
        "label": "Kredkowa / dziecięca",
        "style_block": (
            "Childlike CRAYON DRAWING on paper (drawn with crayons or color "
            "pencils — this is NOT a photograph, NOT photorealistic, NOT a "
            "real child). Naive hand-drawn lines, visible paper texture, "
            "bright primary colors, charming imperfect character."
        ),
    },
}

DEFAULT_ART_STYLE = "storybook"


def style_block(art_style: str | None) -> str:
    return ART_STYLES.get(art_style or DEFAULT_ART_STYLE, ART_STYLES[DEFAULT_ART_STYLE])["style_block"]


DEFAULT_REFERENCE_SYSTEM_PROMPT = """\
You are a visual prompt engineer creating a single character reference sheet for a children's storybook.

OUTPUT: Exactly ONE image prompt. No separators, no numbering, no commentary — just the prompt text.

CHARACTER:
- {name}, {age} years old, {gender}
- {hair_color} hair, {haircut} hairstyle
- {skin_tone} skin tone, {eye_color} eyes
- Clothing: {outfit_description}

STYLE LOCK (MUST be obeyed — leads every prompt):
{style_block}
- Lighting: Soft even lighting (this is a reference sheet, not a scene)

THE PROMPT MUST DESCRIBE:
"Full-body character reference sheet. {style_block} {name}, a {age}-year-old {gender} with {skin_tone} skin, {eye_color} eyes, and {hair_color} {haircut} hair, wearing {outfit_description}. Standing in a neutral pose, front-facing, clear full-body view. Plain white background. No text, no environment, no other characters. --ar 1:1"

You may rephrase for clarity but preserve every physical attribute exactly AND keep the "NOT a photograph" wording from the style block — image models otherwise default to photorealism.
"""


DEFAULT_PAGE_SYSTEM_PROMPT = """\
You are a visual prompt engineer creating scene prompts for a children's storybook.

INPUT: A 15-part story about {name}. A character reference sheet already exists.
OUTPUT: Exactly 15 prompts separated by #########, one per story segment.

NOTE: Cover and back-cover prompts are NOT your job — they are generated separately
by the system. Do not produce them. Generate ONLY the 15 story-page prompts.

CHARACTER REFERENCE (must be consistent across every scene — a reference image already exists):
- {name}, {age} years old, {gender}
- {hair_color} hair, {haircut} hairstyle
- {skin_tone} skin tone, {eye_color} eyes
- Clothing: {outfit_description}

STYLE LOCK (MUST be obeyed and copy-pasted into every prompt):
{style_block}
Lighting: Warm golden hour unless scene requires otherwise.

PROMPT TEMPLATE (15 story illustrations):
"[Scene from story segment]. {style_block} {name}, a {age}-year-old {gender} with {skin_tone} skin, {eye_color} eyes, and {hair_color} {haircut} hair, wearing {outfit_description}. [Action and expression]. [Environment and lighting]. [Composition: wide/medium/close-up]. --ar 1:1"

CRITICAL RULES:
- Character description MUST be copy-pasted identically in every prompt. No variation. No new characters.
- ONLY {name} appears in illustrations. No other humanoid characters.
- The STYLE LOCK block (including the "NOT a photograph" wording) MUST appear in every prompt — image models default to photorealism otherwise.
- One clear focal action per scene. No split scenes.
- Specify shot type: establishing wide, medium, or close-up.
- Include emotional state: expression of wonder, determination, etc."""


DEFAULT_COVER_PROMPT_TEMPLATE = (
    "Children's book cover. {style_block} {name}, a {age}-year-old {gender} "
    "with {skin_tone} skin, {eye_color} eyes, {hair_color} {haircut} hair, "
    "wearing {outfit_description}. Dynamic confident pose in a magical "
    "{story_type} setting that hints at {hobby}. Title text 'Przygoda {name}' "
    "at top in playful hand-drawn font. Vibrant, magical atmosphere. --ar 1:1"
)

DEFAULT_BACK_PROMPT_TEMPLATE = (
    "Children's book back cover. {style_block} Soft, warm scene with a single "
    "symbolic object representing {moral}. No people, no characters, no "
    "humanoid figures — only the object. Text 'Koniec' centered in playful "
    "hand-drawn font. Gentle sunset lighting, dreamy atmosphere. --ar 1:1"
)


def build_reference_system_prompt(project: dict, custom_prompt: str | None = None) -> str:
    template = custom_prompt or DEFAULT_REFERENCE_SYSTEM_PROMPT
    return template.format(
        name=project["child_name"],
        age=project["child_age"],
        gender=project["child_gender"],
        hair_color=project["hair_color"],
        haircut=project["hair_style"],
        skin_tone=project["skin_tone"],
        eye_color=project["eye_color"],
        outfit_description=project["outfit_description"],
        moral=project.get("moral", ""),
        style_block=style_block(project.get("art_style")),
    )


def build_reference_user_prompt(project: dict) -> str:
    return (
        f"Produce the character reference sheet prompt for {project['child_name']}, "
        f"a {project['child_age']}-year-old {project['child_gender']}. "
        "Return only the prompt text, no separators."
    )


def build_page_system_prompt(project: dict, custom_prompt: str | None = None) -> str:
    template = custom_prompt or DEFAULT_PAGE_SYSTEM_PROMPT
    return template.format(
        name=project["child_name"],
        age=project["child_age"],
        gender=project["child_gender"],
        hair_color=project["hair_color"],
        haircut=project["hair_style"],
        skin_tone=project["skin_tone"],
        eye_color=project["eye_color"],
        outfit_description=project["outfit_description"],
        style_block=style_block(project.get("art_style")),
        moral=project["moral"],
    )


def build_page_user_prompt(project: dict, story_text: str, reference_prompt: str | None = None) -> str:
    ref_block = ""
    if reference_prompt:
        ref_block = (
            "The character reference sheet prompt (already used to generate the reference image — "
            "stay consistent with its physical description):\n"
            f"{reference_prompt}\n\n"
        )
    return (
        ref_block
        + f"Here is the 15-part story about {project['child_name']}:\n\n"
        + f"{story_text}\n\n"
        + "Generate exactly 15 image prompts separated by #########, one per "
          "story segment. Do NOT produce a cover prompt or a back-cover prompt — "
          "those are built by the system separately."
    )


def build_cover_image_prompt(project: dict) -> str:
    """Deterministic Python-built cover prompt. Bypasses the LLM so a custom
    page system prompt cannot break the cover's structure (title text, character
    visible, etc.)."""
    return DEFAULT_COVER_PROMPT_TEMPLATE.format(
        name=project["child_name"],
        age=project["child_age"],
        gender=project["child_gender"],
        hair_color=project["hair_color"],
        haircut=project["hair_style"],
        skin_tone=project["skin_tone"],
        eye_color=project["eye_color"],
        outfit_description=project["outfit_description"],
        style_block=style_block(project.get("art_style")),
        story_type=project.get("story_type") or "fairytale",
        hobby=project.get("hobby") or "their adventure",
    )


def build_back_image_prompt(project: dict) -> str:
    """Deterministic Python-built back-cover prompt. No character reference is
    used at gen time (see _build_page_reference_images) — back is a clean
    symbolic-object scene with the 'Koniec' title."""
    return DEFAULT_BACK_PROMPT_TEMPLATE.format(
        moral=project.get("moral") or "a heartwarming life lesson",
        style_block=style_block(project.get("art_style")),
    )


# --- Backward-compatibility shims ---
# The old `image_system_prompt` key in `settings` and the old `build_image_*` helpers
# are replaced by the split above. Keep a minimal alias so code importing the old
# names doesn't break during migration.
DEFAULT_IMAGE_SYSTEM_PROMPT = DEFAULT_PAGE_SYSTEM_PROMPT
