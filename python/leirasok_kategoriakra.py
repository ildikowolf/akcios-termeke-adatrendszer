import csv
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILES = list(BASE_DIR.glob("akcios_termekek_*.csv"))
OUTPUT_FILE = BASE_DIR / "tisztitott_leirasok.csv"


def normalize_numbers(text: str) -> str:
    """
    Csak a számok közötti szóközt törli.
    Példa:
    2 300 -> 2300
    1 316 Ft/l -> 1316 Ft/l
    """
    return re.sub(r"\b(\d{1,3})\s+(\d{3})\b", r"\1\2", text)


def normalize_unit_prices(text: str) -> str:
    """
    Egységárak normalizálása:
    Ft/1 kg -> Ft/kg
    Ft/1 l  -> Ft/l
    """
    text = re.sub(r"ft\s*/\s*1\s*kg", "Ft/kg", text, flags=re.IGNORECASE)
    text = re.sub(r"ft\s*/\s*1\s*l", "Ft/l", text, flags=re.IGNORECASE)
    text = re.sub(r"ft\s*/\s*1\s*db", "Ft/db", text, flags=re.IGNORECASE)
    return text


def normalize_numbers_separators(text: str) -> str:
    """
    Magyar formátumú számokat normalizál:
    1.799,33 -> 1799.33
    2.999 -> 2999
    1,5 -> 1.5
    """
    # ezreselválasztó pont törlése
    text = re.sub(r"(?<=\d)\.(?=\d{3}(?:\D|$))", "", text)

    # tizedesvessző -> tizedespont
    text = re.sub(r"(?<=\d),(?=\d)", ".", text)

    return text


def clean_special_characters(text: str) -> str:
    """
    Meghagyja a leírás szempontjából fontos karaktereket,
    a többi zavaró speciális karaktert szóközre cseréli.
    Meghagyja:
    betűk, számok, szóköz, vessző, pont, /, %, :, ×, +, °, -
    """
    text = re.sub(r"[^0-9A-Za-zÁÉÍÓÖŐÚÜŰáéíóöőúüű\s,./%:×+°-]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def remove_tesco_unavailable_block(text: str) -> str:
    patterns = [
        # eredeti forma
        r"A termék a következő áruházainkban nem kapható:.*",

        # általánosabb fallback (ha nincs idézőjel)
        r"A termék a .* áruházunkban nem kapható.*",
    ]

    for pattern in patterns:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)

    return re.sub(r"\s+", " ", text).strip()


def remove_loyalty_prefix(text: str) -> str:
    """
    Eltávolítja a kártyás prefixeket akkor is,
    ha nem pontosan a sor elején vagy nem pontosan ':' előtt állnak.
    """
    patterns = [
        r"\bclubcarddal\s*:?\s*",
        r"\bbizalomkártyával\s*:?\s*",
        r"\bsupershop kártyával\s*:?\s*",
        r"\blidl plus alkalmazással\s*:?\s*",
    ]

    for pattern in patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    return re.sub(r"\s+", " ", text).strip()


def remove_useless_words(text: str) -> str:
    """
    Eltávolítja a felesleges kötőszavakat a leírásból.
    """
    stopwords = [
        "vagy",
        "meg",
        "és",
    ]

    words = text.split()

    filtered = [
        word for word in words
        if word.lower() not in stopwords
    ]

    return " ".join(filtered)


def remove_bad_prefix(text: str) -> str:
    """
    Levágja a rossz prefixeket a sor elejéről.
    Példák:
    Ft/db, származási hely Magyarország -> származási hely Magyarország
    Ft/kg, csont nélkül -> csont nélkül
    """
    text = re.sub(r"^\s*ft\s*/\s*[a-záéíóöőúüű]+\s*,\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^\s*/\s*[a-záéíóöőúüű]+\s*,\s*", "", text, flags=re.IGNORECASE)
    return text.strip()


def is_product_identifier(text: str) -> bool:
    """
    Hosszú számok kiszűrése, ha nincs mellettük Ft.
    Példa:
    705862 -> törlendő
    4369 Ft/kg -> nem törlendő
    """
    value = text.strip()
    if re.fullmatch(r"\d{5,}", value) and not re.search(r"ft", value, flags=re.IGNORECASE):
        return True
    return False


def remove_trailing_product_identifier(text: str) -> str:
    return re.sub(r"\s+\d{5,}$", "", text).strip()


def is_incomplete_unit(text: str) -> bool:
    """
    Fél / hiányos mértékegységek kiszűrése.
    Ezek akkor törlendők, ha előttük nincs szám.
    """
    value = text.strip().lower()

    patterns = [
        r"^/[a-záéíóöőúüű0-9]+$",
        r"^ft\s*/\s*[a-záéíóöőúüű]+$",
        r"^ft\s*/\s*\d+\s*[a-záéíóöőúüű]+$",
    ]

    return any(re.fullmatch(p, value, flags=re.IGNORECASE) for p in patterns)


def is_standalone_unit(text: str) -> bool:
    value = text.strip().lower()

    standalone_units = {
        "Ft",
        "kg", "g", "dkg", "mg",
        "l", "dl", "cl", "ml",
        "db", "darab",
        "cm", "mm", "m",
        "%"
    }

    return value in standalone_units


def compact_number_units(text: str) -> str:
    units = [
        "Ft/kg", "Ft/g", "Ft/l", "Ft/ml", "Ft/db",
        "Ft",
        "kg", "g", "dkg", "mg",
        "l", "dl", "cl", "ml",
        "db", "darab",
        "cm", "mm", "m",
        "%"
    ]

    unit_pattern = "|".join(re.escape(unit) for unit in units)

    # szám + szóköz + egység → szám+egység
    text = re.sub(
        rf"(\d+(?:\.\d+)?)\s+({unit_pattern})\b",
        r"\1\2",
        text,
        flags=re.IGNORECASE
    )

    # szám × szám + egység → szám×szám+egység
    text = re.sub(
        rf"(\d+)\s*×\s*(\d+(?:\.\d+)?)\s*({unit_pattern})\b",
        r"\1×\2\3",
        text,
        flags=re.IGNORECASE
    )

    return text


def is_promotion_text(text: str) -> bool:
    value = text.lower()

    patterns = [
        r"vásárlása\s+esetén",
        r"legalább\s*\d+",
        r"minden\s+második\s+termék",
        r"termék\s+ára",
        r"\d+\s*\+\s*\d+",           # pl. 3+1, 2+1 stb.
        r"\d+-at\s+fizet",           # 3-at fizet
        r"\d+-et\s+kap",             # 4-et kap
        r"fizet\s+\d+",              # fizet 3
        r"kap\s+\d+",                # kap 4
    ]

    return any(re.search(p, value) for p in patterns)


def is_empty_or_useless(text: str) -> bool:
    value = text.strip()

    if not value:
        return True

    # csak írásjelek vagy zárójelek
    if re.fullmatch(r"[/,.%:()\-]+", value):
        return True

    return False


def clean_value(text: str) -> str:
    text = normalize_numbers(text)
    text = normalize_numbers_separators(text)
    text = normalize_unit_prices(text)
    text = clean_special_characters(text)
    text = remove_loyalty_prefix(text)
    text = remove_bad_prefix(text)
    text = remove_useless_words(text)
    text = compact_number_units(text)
    text = remove_trailing_product_identifier(text)
    text = re.sub(r"\s+", " ", text).strip(" ,./")
    return text


def split_description(text: str) -> list[str]:
    if not text:
        return []

    text = remove_tesco_unavailable_block(text)
    text = normalize_numbers(text)
    text = normalize_numbers_separators(text)

    raw_parts = [part.strip() for part in text.split("|")]

    parts = []

    for raw_part in raw_parts:
        if not raw_part:
            continue

        # akció szöveg egyben marad
        if is_promotion_text(raw_part):
            parts.append(raw_part)
            continue

        # normál szöveg → vessző mentén bontjuk
        subparts = re.split(r"(?<!\d),(?!\d)", raw_part)

        for subpart in subparts:
            subpart = subpart.strip(" ,")
            if subpart:
                parts.append(subpart)

    cleaned_parts = []

    for part in parts:
        if is_product_identifier(part):
            continue

        if is_incomplete_unit(part):
            continue

        part = clean_value(part)

        if is_empty_or_useless(part):
            continue

        if is_standalone_unit(part):
            continue

        cleaned_parts.append(part)

    return cleaned_parts


def main() -> None:
    output_rows = []

    for input_file in INPUT_FILES:
        if not input_file.exists():
            print(f"Nem található a bemeneti fájl: {input_file}")
            continue

        with open(input_file, "r", encoding="utf-8-sig", newline="") as infile:
            reader = csv.DictReader(infile)

            for row in reader:
                leiras = row.get("leiras") or ""
                egyedi_hash = (row.get("egyedi_hash") or "").strip()

                values = split_description(leiras)

                for value in values:
                    output_rows.append({

                        "ertek": value,
                        "egyedi_hash": egyedi_hash
                    })

    with open(OUTPUT_FILE, "w", encoding="utf-8-sig", newline='') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=["ertek", "egyedi_hash"])
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"Kész. Mentett sorok száma: {len(output_rows)}")
    print(f"Kimeneti fájl: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
