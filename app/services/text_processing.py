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


stop_words = {"ir", "bet", "kad", "su", "į", "iš", "ar"}

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