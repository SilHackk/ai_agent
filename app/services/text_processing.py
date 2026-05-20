#Čia naudojami klasikiniai NLP metodai: teksto valymas, tokenizacija ir stop words šalinimas.
import re
from collections import Counter

def extract_keywords(filtered_words, top_n=10):
    return Counter(filtered_words).most_common(top_n)

def preprocess_text(text):
    text = text.lower()
    text = re.sub(r'<.*?>', '', text)
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def tokenize(text):
    words = text.split()
    sentences = text.split('.')
    return words, sentences


stop_words = {
    "ir", "bet", "kad", "su", "į", "iš", "ar", "bei",
    "o", "aš", "as", "mes", "jus", "jūs", "man", "mums",
    "laba", "diena", "sveiki", "sveikas", "sveika",
    "labas", "labadiena", "hi", "hello",

    "noriu", "norime", "norėčiau", "noreciau",
    "reikia", "gal", "galima", "domina",
    "ieškau", "ieskau", "planuoju",

    "viskas", "gerai", "ane", "taip", "ne",
    "tik", "dar", "jau", "čia", "cia",
    "ten", "šitas", "sitas", "tas",
    "šitie", "sitie",

    "prašau", "prasau", "ačiū", "aciu",
    "dėkoju", "dekui",

    "dėl", "del", "apie", "pagal",
    "nuo", "iki", "po", "prie",

    "būtų", "butu", "yra", "buvo",
    "esu", "esame", "bus", "busime",

    "kokia", "koks", "kokie", "kuri",
    "kuris", "kurie",

    "mano", "mūsų", "musu", "jūsų",
    "jusu", "savo",

    "labai", "truputi", "šiek", "siektiek",
    "maždaug", "mazdaug",

    "atsiųsti", "atsiuskite", "atsiųskite",
    "paskambinti", "susisiekti",

    "projektas", "objektas", "variantas",
    "sprendimas"
}

def remove_stopwords(words):
    return [w for w in words if w not in stop_words]

def classify_request_type(text: str) -> str:
    text = text.lower()

    if any(word in text for word in ["kaina", "sąmata", "pasiūlymas", "kainos"]):
        return "Kainos užklausa"

    if any(word in text for word in ["terminas", "pagaminti", "pristatymas", "kada"]):
        return "Terminų užklausa"

    if any(word in text for word in ["brėžinys", "schema", "projektas", "pdf"]):
        return "Techninė užklausa"

    return "Bendra užklausa"

def extract_city(text: str):
    cities = ["vilnius", "kaunas", "klaipėda", "šiauliai", "panevėžys"]
    text = text.lower()

    for city in cities:
        if city in text:
            return city.capitalize()

    return None