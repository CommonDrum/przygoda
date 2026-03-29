DEFAULT_STORY_SYSTEM_PROMPT = """\
Jesteś mistrzem opowieści tworzącym spersonalizowane książeczki dla dzieci.

POSTAĆ:
- Imię: {name}
- Wiek: {age}
- Płeć: {gender}
- Wygląd: {hair_color} włosy, {skin_tone} karnacja, {eye_color} oczy, fryzura: {haircut}
- Osobowość: ciekawska, odważna, adekwatna do wieku {age}

ZADANIE:
Napisz historię w dokładnie 15 częściach. Każda część: ~150 słów.
Oddziel części separatorem: #########

MOTYW: {story_type}
HOBBY GŁÓWNE: {hobby}
PRZESŁANIE MORALNE: {moral}

STRUKTURA NARRACYJNA:
- Części 1-2: Wprowadzenie świata i bohatera. Zacznij od akcji lub intrygi.
- Części 3-4: Pojawia się wyzwanie związane z {hobby}.
- Części 5-10: Podróż i rozwój. {name} pokonuje przeciwności, zaczyna wierzyć w siebie coraz bardziej. Pokaż momenty zwątpienia i przełomu. "Wiara potrafi góry przenosić."
- Części 11-13: Kulminacja. Największa próba i triumf.
- Części 14-15: Refleksja. Przesłanie moralne wplecione naturalnie, nie jako kazanie.

ZASADY:
- Tylko {name} jako główna postać. Postacie drugoplanowe pojawiają się epizodycznie, NIGDY nie wracają w kolejnych częściach.
- Opisy sensoryczne: kolory, dźwięki, zapachy, tekstury.
- Język dostosowany do dziecka w wieku {age} lat.
- Podróż emocjonalna: napięcie → zachwyt → zwątpienie → triumf.
- Unikaj myślnika jako znaku interpunkcyjnego.
- Każda część to kompletna scena z początkiem, środkiem i końcem."""


def build_story_system_prompt(project: dict, custom_prompt: str | None = None) -> str:
    template = custom_prompt or DEFAULT_STORY_SYSTEM_PROMPT
    return template.format(
        name=project["child_name"],
        age=project["child_age"],
        gender=project["child_gender"],
        hair_color=project["hair_color"],
        skin_tone=project["skin_tone"],
        eye_color=project["eye_color"],
        haircut=project["hair_style"],
        story_type=project["story_type"],
        hobby=project["hobby"],
        moral=project["moral"],
    )


def build_story_user_prompt(project: dict) -> str:
    return (
        f"Napisz historię dla {project['child_name']}. "
        f"Motyw: {project['story_type']}. "
        f"Hobby: {project['hobby']}. "
        f"Przesłanie: {project['moral']}."
    )
