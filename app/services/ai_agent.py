from openai import OpenAI
from app.core.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)


def analyze_request(email_text: str, pdf_text: str = "") -> str:
    prompt = f"""
Tu esi langų įmonės AI asistentas.

Tavo užduotis:
1. Nustatyti kliento užklausos kategoriją.
2. Ištraukti svarbią informaciją iš email ir PDF.
3. Patikrinti, ko trūksta prieš perduodant užklausą skaičiavimui MBcad / Klaes programose.
4. Paruošti atsakymo juodraštį klientui.
5. Paruošti aiškią suvestinę darbuotojui.

Svarbu:
- Galutinės kainos neskaičiuok, nes kainynai yra MBcad.
- Jei duomenys neaiškūs, pažymėk, kad reikia žmogaus patikrinimo.
Atsakymą pateik tik tokiu formatu:

## Kategorija
...

## Ištraukti duomenys
- Klientas:
- Miestas:
- Objektas:
- Ar yra PDF/projektas:
- Ar reikia montavimo:
- Langų kiekis:
- Matmenys:
- Papildomi pageidavimai:

## Ko trūksta
- ...

## Atsakymo juodraštis klientui
...

## MBcad / Klaes suvestinė darbuotojui
- ...
Jei informacijos nėra, rašyk „Nenurodyta“, o ne spėliok.
- Sistema nepakeičia MBcad, tik paruošia informaciją darbui.

EMAIL TEKSTAS:
{email_text}

PDF TEKSTAS:
{pdf_text}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Tu esi profesionalus AI asistentas langų gamybos įmonei."},
            {"role": "user", "content": prompt}
        ],
        max_completion_tokens=900,
        temperature=0.2
    )

    return response.choices[0].message.content