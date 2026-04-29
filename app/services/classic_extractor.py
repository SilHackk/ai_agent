import re


PRODUCT_KEYWORDS = {
    "langai": ["langas", "langai", "langų", "langu"],
    "durys": ["durys", "durų", "duru", "duris"],
    "vitrinos": ["vitrina", "vitrinos", "vitrinų", "vitrinu"],
    "stoglangiai": ["stoglangis", "stoglangiai", "velux"]
}

SERVICE_KEYWORDS = {
    "gamyba": ["pagaminti", "gamyba", "užsakyti", "uzsakyti"],
    "montavimas": ["montavimas", "montuoti", "sumontuoti"],
    "konsultacija": ["konsultacija", "pasikonsultuoti", "patarti"],
    "pasiūlymas": ["pasiūlymas", "pasiulymas", "kaina", "sąmata", "samata"]
}

URGENCY_KEYWORDS = [
    "skubiai",
    "kuo greičiau",
    "kuo greiciau",
    "šią savaitę",
    "sia savaite",
    "iki rytojaus"
]

MATERIAL_KEYWORDS = [
    "plastikiniai",
    "plastikinis",
    "aliuminiai",
    "aliuminis",
    "mediniai",
    "medinis",
    "pvc"
]

COLOR_KEYWORDS = [
    "balta",
    "juoda",
    "antracitas",
    "pilka",
    "ruda",
    "ral 7016",
    "ral7016"
]

CITIES = [
    "vilnius", "kaunas", "klaipėda", "klaipeda",
    "šiauliai", "siauliai", "panevėžys", "panevezys",
    "alytus", "marijampolė", "marijampole"
]


def tokenize(text: str) -> list[str]:
    text = text.lower()
    return re.findall(r"\b[\wąčęėįšųūž]+\b", text)


def extract_dimensions(text: str) -> list[str]:
    pattern = r"\b\d{2,5}\s*[x×]\s*\d{2,5}\s*(?:mm|cm|m)?\b"
    return re.findall(pattern, text.lower())


def extract_quantities(text: str) -> list[str]:
    pattern = r"\b\d+\s*(?:vnt\.?|vienetai|langai|langų|langu|durys|durų|duru)\b"
    return re.findall(pattern, text.lower())


def extract_emails(text: str) -> list[str]:
    pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
    return re.findall(pattern, text)


def extract_phones(text: str) -> list[str]:
    pattern = r"(?:\+370|8)\s?\d{3}\s?\d{5}|\+370\s?\d{3}\s?\d{5}"
    return re.findall(pattern, text)


def extract_cities(text: str) -> list[str]:
    lower_text = text.lower()
    return [city for city in CITIES if city in lower_text]


def extract_keywords(text: str, keyword_dict: dict) -> list[str]:
    lower_text = text.lower()
    found = []

    for label, keywords in keyword_dict.items():
        if any(keyword in lower_text for keyword in keywords):
            found.append(label)

    return found


def extract_simple_keywords(text: str, keywords: list[str]) -> list[str]:
    lower_text = text.lower()
    return [keyword for keyword in keywords if keyword in lower_text]


def detect_missing_info(extracted: dict) -> list[str]:
    missing = []

    if not extracted["dimensions"]:
        missing.append("matmenys")

    if not extracted["quantities"]:
        missing.append("kiekis")

    if not extracted["cities"]:
        missing.append("miestas / objektas")

    if not extracted["colors"]:
        missing.append("spalva")

    if not extracted["materials"]:
        missing.append("profilio / medžiagos tipas")

    return missing


def extract_classic_features(text: str) -> dict:
    tokens = tokenize(text)

    extracted = {
        "tokens": tokens,
        "dimensions": extract_dimensions(text),
        "quantities": extract_quantities(text),
        "emails": extract_emails(text),
        "phones": extract_phones(text),
        "cities": extract_cities(text),
        "product_types": extract_keywords(text, PRODUCT_KEYWORDS),
        "services": extract_keywords(text, SERVICE_KEYWORDS),
        "urgency": extract_simple_keywords(text, URGENCY_KEYWORDS),
        "materials": extract_simple_keywords(text, MATERIAL_KEYWORDS),
        "colors": extract_simple_keywords(text, COLOR_KEYWORDS),
    }

    extracted["missing_info"] = detect_missing_info(extracted)

    return extracted