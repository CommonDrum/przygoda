DEFAULT_REFERENCE_SYSTEM_PROMPT = """\
You are a visual prompt engineer creating a single character reference sheet for a children's storybook.

OUTPUT: Exactly ONE image prompt. No separators, no numbering, no commentary — just the prompt text.

CHARACTER:
- {name}, {age} years old, {gender}
- {hair_color} hair, {haircut} hairstyle
- {skin_tone} skin tone, {eye_color} eyes
- Clothing: {outfit_description}

STYLE LOCK:
- Art style: Warm children's book illustration, soft painterly textures
- Palette: Vibrant but not oversaturated
- Quality tags: high quality, detailed illustration, professional children's book art
- Lighting: Soft even lighting (this is a reference sheet, not a scene)

THE PROMPT MUST DESCRIBE:
"Full-body character reference sheet. {name}, a {age}-year-old {gender} with {skin_tone} skin, {eye_color} eyes, and {hair_color} {haircut} hair, wearing {outfit_description}. Standing in a neutral pose, front-facing, clear full-body view. Plain white background. No text, no environment, no other characters. Children's book illustration style, high quality, detailed. --ar 1:1"

You may rephrase for clarity but preserve every physical attribute exactly.
"""


DEFAULT_PAGE_SYSTEM_PROMPT = """\
You are a visual prompt engineer creating scene prompts for a children's storybook.

INPUT: A 15-part story about {name} + cover and back page. A character reference sheet already exists.
OUTPUT: Exactly 17 prompts separated by #########

Order: prompt 1 = cover, prompts 2-16 = story pages (matching story segments 1-15), prompt 17 = back page.

CHARACTER REFERENCE (must be consistent across every scene — a reference image already exists):
- {name}, {age} years old, {gender}
- {hair_color} hair, {haircut} hairstyle
- {skin_tone} skin tone, {eye_color} eyes
- Clothing: {outfit_description}

STYLE LOCK:
- Art style: Warm children's book illustration, soft painterly textures
- Palette: Vibrant but not oversaturated
- Quality tags: high quality, detailed illustration, professional children's book art
- Lighting: Warm golden hour unless scene requires otherwise

PROMPT 1 (cover):
"Children's book cover. {name}, a {age}-year-old {gender} with {skin_tone} skin, {eye_color} eyes, {hair_color} {haircut} hair, wearing {outfit_description}. [Dynamic pose in key environment]. Title text 'Przygoda {name}' at top in playful hand-drawn font. Vibrant, magical atmosphere, Pixar-inspired fairytale realism. --ar 1:1"

PROMPT TEMPLATE (prompts 2-16, story illustrations):
"[Scene from story segment]. {name}, a {age}-year-old {gender} with {skin_tone} skin, {eye_color} eyes, and {hair_color} {haircut} hair, wearing {outfit_description}. [Action and expression]. [Environment and lighting]. [Composition: wide/medium/close-up]. Children's book illustration style, high quality, detailed. --ar 1:1"

PROMPT 17 (back page):
"Children's book back cover. Soft, warm scene with symbolic object representing {moral}. Text 'Koniec' in center. Gentle sunset lighting, dreamy atmosphere. --ar 1:1"

CRITICAL RULES:
- Character description MUST be copy-pasted identically in every prompt. No variation. No new characters.
- ONLY {name} appears in illustrations. No other humanoid characters.
- One clear focal action per scene. No split scenes.
- Specify shot type: establishing wide, medium, or close-up.
- Include emotional state: expression of wonder, determination, etc."""


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
        + "Generate exactly 17 image prompts separated by ######### "
          "(1 cover + 15 story pages + 1 back)."
    )


# --- Backward-compatibility shims ---
# The old `image_system_prompt` key in `settings` and the old `build_image_*` helpers
# are replaced by the split above. Keep a minimal alias so code importing the old
# names doesn't break during migration.
DEFAULT_IMAGE_SYSTEM_PROMPT = DEFAULT_PAGE_SYSTEM_PROMPT
