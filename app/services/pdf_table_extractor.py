#Papildomai bandoma ištraukti PDF lenteles ir techninius duomenis
import re


def extract_window_tables_from_text(pdf_text: str) -> list[dict]:
    """
    Bando iš PDF tekstinio sluoksnio ištraukti langų/gaminių lentelės informaciją.
    Veikia, jei PDF tekstas yra nuskaitomas kaip tekstas, o ne tik paveikslas.
    """

    rows = []

    lines = pdf_text.splitlines()

    for line in lines:
        clean_line = line.strip()

        if not clean_line:
            continue

        # Ieško langų žymėjimų, pvz. L1, L-01, W1, W-02
        label_match = re.search(r"\b(L|W)[-]?\d+\b", clean_line, re.IGNORECASE)

        # Ieško matmenų, pvz. 1200x1500, 1200 x 1500, 1200×1500
        dimension_match = re.search(
            r"(\d{2,4})\s*[xX×]\s*(\d{2,4})",
            clean_line
        )

        # Ieško kiekio, pvz. 2 vnt, 2 pcs, kiekis 2
        quantity_match = re.search(
            r"(?:kiekis|qty|vnt|pcs)?\s*(\d+)\s*(?:vnt|pcs)?",
            clean_line,
            re.IGNORECASE
        )

        # Ieško spalvos
        color_match = re.search(
            r"(balta|juoda|pilka|antracitas|ruda|auksinis azuolas|ąžuolas|ral\s?\d{4})",
            clean_line,
            re.IGNORECASE
        )

        if label_match or dimension_match:
            row = {
                "zymejimas": label_match.group(0) if label_match else None,
                "plotis_mm": int(dimension_match.group(1)) if dimension_match else None,
                "aukstis_mm": int(dimension_match.group(2)) if dimension_match else None,
                "kiekis": int(quantity_match.group(1)) if quantity_match else None,
                "spalva": color_match.group(0) if color_match else None,
                "originali_eilute": clean_line
            }

            rows.append(row)

    return rows