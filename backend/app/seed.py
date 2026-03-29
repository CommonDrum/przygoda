"""Seed database with a demo project in 'review' status with mock data."""
import os

from PIL import Image, ImageDraw, ImageFont

from .config import UPLOADS_DIR


STORY_SEGMENTS = [
    "Zosia obudziła się wcześnie rano, kiedy pierwsze promienie słońca wpadły przez okno jej pokoju. Na parapecie leżał tajemniczy list w złotej kopercie. Otworzyła go drżącymi rękami — w środku znajdowała się mapa prowadząca do Magicznego Lasu, gdzie kolory ożywają i tańczą w powietrzu. Zosia chwyciła swój ulubiony pędzel i ruszyła w drogę.",
    "Ścieżka prowadziła przez łąkę pełną kwiatów, które pachniały jak świeże farby. Każdy kwiat miał inny, intensywny kolor — turkusowy, koralowy, złoty. Zosia zatrzymała się, żeby narysować je w swoim szkicowniku. Nagle jeden z kwiatów zamrugał do niej płatkami i wskazał kierunek dalszej drogi.",
    "Na skraju lasu Zosia zobaczyła wielkie drzewo, którego kora wyglądała jak paleta malarza. Dotknęła pnia i poczuła ciepło — drzewo pulsowało kolorami. Z dziupli wypadł mały pędzel, który świecił złotym blaskiem. Kiedy Zosia go podniosła, poczuła jak przepływa przez nią fala energii.",
    "Z magicznym pędzlem w ręku Zosia weszła głębiej w las. Drzewa tutaj były szare i smutne — ktoś zabrał im kolory. Zosia próbowała malować, ale pędzel nie działał. Sfrustrowana usiadła na kamieniu. Czy naprawdę potrafi przywrócić kolory temu miejscu?",
    "Zamknęła oczy i wzięła głęboki oddech. Przypomniała sobie słowa babci: wiara potrafi góry przenosić. Otworzyła oczy i spróbowała jeszcze raz — tym razem nie myślała o technice, tylko o tym, jak bardzo kocha kolory. Pędzel rozbłysnął i pierwsze drzewo pokryło się soczystą zielenią.",
    "Zosia malowała coraz śmielej. Każde pociągnięcie pędzla przywracało kolor innemu drzewu. Brzozy stawały się srebrno-białe, dęby ciemnobrązowe, a klony eksplodowały pomarańczem i czerwienią. Las zaczynał śpiewać — ptaki wracały na kolorowe gałęzie.",
    "Ale w głębi lasu czekało wyzwanie. Zosia natknęła się na ogromną polanę, która była całkowicie czarna — jakby ktoś rozlał na nią atrament. Pędzel w jej ręku zadrżał. To było za dużo, za duża przestrzeń. Zosia poczuła, że jej pewność siebie znika jak poranny mgła.",
    "Usiadła na mokrej trawie i patrzyła na czarną polanę. Łzy napłynęły jej do oczu. Ale wtedy zobaczyła coś — mały, samotny kwiatek przebijał się przez czarną ziemię. Był blady, prawie biały, ale walczył o życie. Jeśli on nie poddaje się, ona też nie może.",
    "Zosia wstała i zaczęła malować od tego kwiatka. Delikatnie, ostrożnie, nadała mu kolor — jasny róż. Potem namalowała trawę wokół niego, potem kolejny kwiatek, i kolejny. Nie próbowała pomalować całej polany naraz. Krok po kroku, kwiatek po kwiatku.",
    "Godziny mijały, a Zosia malowała bez przerwy. Polana zamieniała się w najpiękniejszy ogród, jaki ktokolwiek widział. Motyle w kolorach tęczy zatańczyły wokół niej. Każdy kolor był żywszy i bardziej intensywny niż gdziekolwiek indziej w lesie.",
    "Nagle pędzel zaczął świecić jaśniej niż kiedykolwiek. Zosia poczuła, że las jej dziękuje. Ostatnie szare plamy na najstarszym dębie zniknęły pod jej dotykiem. Cały Magiczny Las odzyskał swoje kolory — lśnił tysiącami odcieni, migotał w świetle słońca.",
    "Las zagrał melodię z szumu liści i śpiewu ptaków — to była pieśń dziękczynna. Zosia stanęła na środku polany, a wokół niej wirowały kolorowe liście. Czuła się silna, odważna i pewna siebie. Dokonała czegoś, w co na początku nie wierzyła.",
    "Magiczny pędzel powoli zgasł — jego praca dobiegła końca. Ale Zosia wiedziała, że magia nie była w pędzlu. Była w niej samej — w jej wytrwałości, odwadze i miłości do kolorów. Pędzel był tylko narzędziem, prawdziwa siła płynęła z jej serca.",
    "Wracając do domu, Zosia widziała świat innymi oczami. Zwykłe rzeczy wydawały się piękniejsze — zachód słońca nad dachami, zielona trawa w parku, nawet szary chodnik miał swój urok. Każdy kolor opowiadał historię, wystarczyło tylko uważnie patrzeć.",
    "Wieczorem Zosia usiadła przy biurku i otworzyła nowy szkicownik. Nie potrzebowała magicznego pędzla. Wzięła swoje zwykłe kredki i zaczęła rysować — Magiczny Las, polanę z kwiatami, tańczące motyle. Każdy rysunek był pełen życia, bo malowała sercem. A wiara w siebie? Ta została z nią na zawsze.",
]

IMAGE_PROMPTS = [
    "Children's book cover. Zosia, a 5-year-old girl with fair skin, blue eyes, and blonde ponytail hair, wearing a red dress with white polka dots. Dynamic pose holding a glowing paintbrush in a magical colorful forest. Title text 'Przygoda Zosia' at top in playful hand-drawn font. Vibrant, magical atmosphere, Pixar-inspired fairytale realism. --ar 1:1",
    "Zosia waking up in her cozy bedroom, golden sunrise through window. Zosia, a 5-year-old girl with fair skin, blue eyes, and blonde ponytail hair, wearing a red dress. Excited expression discovering a golden envelope on windowsill. Warm morning light, soft shadows. Medium shot. Children's book illustration style, high quality, detailed. --ar 1:1",
    "Zosia walking through a meadow of vibrant oversized flowers. Zosia, a 5-year-old girl with fair skin, blue eyes, and blonde ponytail hair, wearing a red dress. Curious expression, sketchbook in hand. Turquoise, coral and golden flowers surround her. Wide establishing shot. Children's book illustration style. --ar 1:1",
    "Zosia touching a tree trunk that looks like a painter's palette. Zosia, a 5-year-old girl with fair skin, blue eyes, and blonde ponytail hair, wearing a red dress. Amazed expression as a golden brush falls from a hollow. Magical glow, dappled forest light. Medium shot. Children's book illustration style. --ar 1:1",
    "Zosia sitting on a rock in a grey, colorless forest. Zosia, a 5-year-old girl with fair skin, blue eyes, and blonde ponytail hair, wearing a red dress. Frustrated expression, holding a dim magical brush. Sad grey atmosphere, lifeless trees. Wide shot. Children's book illustration style. --ar 1:1",
    "Zosia with closed eyes, taking a deep breath. Zosia, a 5-year-old girl with fair skin, blue eyes, and blonde ponytail hair, wearing a red dress. Determined expression, glowing brush in hand, first tree turning green. Transition from grey to color. Close-up. Children's book illustration style. --ar 1:1",
    "Zosia painting trees with bold sweeping strokes. Zosia, a 5-year-old girl with fair skin, blue eyes, and blonde ponytail hair, wearing a red dress. Joyful expression, birches turning silver, oaks turning brown, maples exploding with orange. Dynamic composition. Wide shot. Children's book illustration style. --ar 1:1",
    "Zosia standing before a vast black clearing. Zosia, a 5-year-old girl with fair skin, blue eyes, and blonde ponytail hair, wearing a red dress. Worried expression, trembling brush. Dramatic contrast between colorful forest behind and black void ahead. Wide establishing shot. Children's book illustration style. --ar 1:1",
    "Zosia sitting on wet grass, tears in her eyes, looking at a tiny pale flower. Zosia, a 5-year-old girl with fair skin, blue eyes, and blonde ponytail hair, wearing a red dress. Emotional close-up, single brave flower pushing through dark ground. Soft diffused light. Children's book illustration style. --ar 1:1",
    "Zosia kneeling, carefully painting the small flower pink. Zosia, a 5-year-old girl with fair skin, blue eyes, and blonde ponytail hair, wearing a red dress. Gentle concentrated expression, color spreading outward. Close-up on hands and flower. Warm intimate light. Children's book illustration style. --ar 1:1",
    "Zosia painting tirelessly, clearing transforming into a garden. Zosia, a 5-year-old girl with fair skin, blue eyes, and blonde ponytail hair, wearing a red dress. Happy exhausted expression, rainbow butterflies dancing. Vibrant explosion of colors. Wide panoramic shot. Children's book illustration style. --ar 1:1",
    "Zosia touching the last grey oak, magical brush glowing intensely. Zosia, a 5-year-old girl with fair skin, blue eyes, and blonde ponytail hair, wearing a red dress. Triumphant expression, entire forest alive with color. Golden magical light. Medium shot. Children's book illustration style. --ar 1:1",
    "Zosia standing in the center of the blooming clearing, colorful leaves swirling. Zosia, a 5-year-old girl with fair skin, blue eyes, and blonde ponytail hair, wearing a red dress. Proud confident expression, arms spread wide. Magical celebratory atmosphere. Wide shot. Children's book illustration style. --ar 1:1",
    "Zosia holding the dimming magical brush, understanding the magic was inside her. Zosia, a 5-year-old girl with fair skin, blue eyes, and blonde ponytail hair, wearing a red dress. Wise peaceful expression, soft golden glow. Forest in full beautiful color behind. Medium close-up. Children's book illustration style. --ar 1:1",
    "Zosia walking home through a beautifully colorful sunset town. Zosia, a 5-year-old girl with fair skin, blue eyes, and blonde ponytail hair, wearing a red dress. Serene happy expression, seeing beauty everywhere. Warm sunset palette. Wide establishing shot. Children's book illustration style. --ar 1:1",
    "Zosia at her desk drawing with regular crayons, her drawings full of life. Zosia, a 5-year-old girl with fair skin, blue eyes, and blonde ponytail hair, wearing a red dress. Content determined expression, colorful drawings spread around. Warm lamp light, cozy bedroom. Medium shot. Children's book illustration style. --ar 1:1",
    "Children's book back cover. Soft warm scene with a single glowing paintbrush resting on a painter's palette surrounded by colorful butterflies. Text 'Koniec' in center in playful font. Gentle sunset lighting, dreamy magical atmosphere. --ar 1:1",
]

# Color palette for placeholder images
PAGE_COLORS = [
    "#6366f1",  # cover - indigo
    "#f59e0b", "#10b981", "#ef4444", "#8b5cf6",  # pages 2-5
    "#06b6d4", "#f97316", "#84cc16", "#ec4899",  # pages 6-9
    "#14b8a6", "#a855f7", "#eab308", "#3b82f6",  # pages 10-13
    "#22c55e", "#e11d48", "#0ea5e9",             # pages 14-16
    "#6b7280",  # back - gray
]


def generate_placeholder_image(page_num: int, label: str, color: str, output_path: str):
    """Generate a colored placeholder image with page number and label."""
    img = Image.new("RGB", (512, 512), color)
    draw = ImageDraw.Draw(img)

    # Draw page number large
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    except OSError:
        font_large = ImageFont.load_default()
        font_small = font_large

    # Center the page number
    text = str(page_num)
    bbox = draw.textbbox((0, 0), text, font=font_large)
    x = (512 - (bbox[2] - bbox[0])) // 2
    draw.text((x, 180), text, fill="white", font=font_large)

    # Label below
    bbox2 = draw.textbbox((0, 0), label, font=font_small)
    x2 = (512 - (bbox2[2] - bbox2[0])) // 2
    draw.text((x2, 280), label, fill="white", font=font_small)

    img.save(output_path, "PNG")


async def seed_demo_project():
    """Insert a full demo project with mock story, prompts, and placeholder images."""
    if os.environ.get("TESTING"):
        return

    from .database import get_db

    db = await get_db()
    try:
        # Check if demo already exists
        cursor = await db.execute("SELECT id FROM projects WHERE child_name = 'Zosia' LIMIT 1")
        if await cursor.fetchone():
            return  # Already seeded

        # Create project
        raw_story = "\n#########\n".join(STORY_SEGMENTS)
        raw_prompts = "\n#########\n".join(IMAGE_PROMPTS)

        cursor = await db.execute(
            """INSERT INTO projects
               (child_name, child_age, child_gender, hair_color, hair_style,
                skin_tone, eye_color, outfit_description, story_type, hobby, moral,
                raw_story, raw_image_prompts, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("Zosia", 5, "dziewczynka", "blond", "kucyk", "jasna", "niebieskie",
             "czerwona sukienka z białymi kropkami",
             "magiczna podróż", "malowanie", "wiara w siebie",
             raw_story, raw_prompts, "review"),
        )
        project_id = cursor.lastrowid

        # Create upload dir
        upload_dir = UPLOADS_DIR / str(project_id)
        os.makedirs(upload_dir, exist_ok=True)

        # Create 17 pages with text, prompts, and placeholder images
        page_defs = []

        # Cover
        page_defs.append((project_id, 1, "cover", f"Przygoda Zosia", IMAGE_PROMPTS[0]))
        # Story pages 2-16
        for i in range(15):
            page_defs.append((project_id, i + 2, "story", STORY_SEGMENTS[i], IMAGE_PROMPTS[i + 1]))
        # Back
        page_defs.append((project_id, 17, "back", "Koniec", IMAGE_PROMPTS[16]))

        for proj_id, page_num, page_type, text, prompt in page_defs:
            # Generate placeholder image
            if page_num == 1:
                label = "Okładka"
            elif page_num == 17:
                label = "Tył okładki"
            else:
                label = f"Strona {page_num - 1}"

            filename = f"page_{page_num}_v1.png"
            filepath = str(upload_dir / filename)
            color = PAGE_COLORS[page_num - 1] if page_num <= len(PAGE_COLORS) else "#6b7280"
            generate_placeholder_image(page_num, label, color, filepath)

            image_path = f"/static/uploads/{proj_id}/{filename}"

            await db.execute(
                """INSERT INTO pages
                   (project_id, page_number, page_type, text, image_prompt,
                    current_image_path, version)
                   VALUES (?, ?, ?, ?, ?, ?, 1)""",
                (proj_id, page_num, page_type, text, prompt, image_path),
            )

            # Also add to image_versions
            await db.execute(
                """INSERT INTO image_versions
                   (page_id, image_path, prompt_used, provider, version_number)
                   VALUES (last_insert_rowid(), ?, ?, 'mock', 1)""",
                (image_path, prompt),
            )

        await db.commit()
    finally:
        await db.close()
