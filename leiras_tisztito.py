import pandas as pd
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "tisztitott_leirasok.csv"
OUTPUT_FILE = BASE_DIR / "jobban_szetszedett_leirasok.csv"


def normalize_text(text):
    if pd.isna(text):
        return ""

    text = str(text).strip()

    text = text.replace("×", "x")
    text = re.sub(r"\s+", " ", text)

    # szám + mértékegység közti felesleges szóköz eltávolítása
    text = re.sub(
        r"(\d+(?:[,.]\d+)?)\s+(kg|g|dkg|l|ml|db|darab|csomag|ft|Ft)",
        r"\1\2",
        text,
        flags=re.IGNORECASE
    )

    # 500g / csomag  →  500g 1db
    text = re.sub(
        r"(\d+(?:[,.]\d+)?(?:kg|g|dkg|l|ml))\s*/\s*csomag",
        r"\1 1db",
        text,
        flags=re.IGNORECASE
    )

    # 500g/csomag → 500g 1db
    text = re.sub(
        r"(\d+(?:[,.]\d+)?(?:kg|g|dkg|l|ml|db|darab|csomag))/csomag",
        r"\1 1db",
        text,
        flags=re.IGNORECASE
    )

    return text.strip()


def extract_parentheses(text):
    """
    Zárójeles részek kiszedése külön elemként.
    Pl.: csomagolt 320g (3746.88Ft/kg)
    -> fő szöveg: csomagolt 320g
    -> zárójeles elem: 3746.88Ft/kg
    """
    parentheses = re.findall(r"\((.*?)\)", text)
    text_without_parentheses = re.sub(r"\(.*?\)", " ", text)
    text_without_parentheses = re.sub(r"\s+", " ", text_without_parentheses).strip()

    return text_without_parentheses, parentheses


def split_by_safe_slash(text):
    """
    Csak akkor vágja szét a / jelet, ha előtte és utána szóköz van.
    Így nem rontja el:
    - Ft/kg
    - Ft/l
    - Ft/db
    """
    return re.split(r"\s+/\s+", text)


def split_mixed_quantity_text(text):
    """
    Szétválasztja az olyan részeket, mint:
    'csomagolt 320g'
    'spenótos-ricottás csomagolt 400g'
    """
    parts = []

    special_patterns = [
    # 867Ft/4db, 289Ft/1db, 316Ft/6db
    r"\d+(?:[,.]\d+)?Ft/\d+(?:[,.]\d+)?(?:kg|g|dkg|l|ml|db|darab|csomag)",

    # 4817Ft/kg, 599Ft/db
    r"\d+(?:[,.]\d+)?Ft/(?:kg|g|dkg|l|ml|db|darab|csomag)",

    # 6x100ml
    r"\d+\s*x\s*\d+(?:[,.]\d+)?(?:kg|g|dkg|l|ml|db)",

    # 320/355g
    r"\d+(?:[,.]\d+)?(?:/\d+(?:[,.]\d+)?)+(?:kg|g|dkg|l|ml|db)",

    # 16db/csomag
    r"\d+(?:[,.]\d+)?(?:kg|g|dkg|l|ml|db|darab)/(?:csomag|darab|db|doboz|üveg|tégely|cs)",
    ]

    protected = []

    for pattern in special_patterns:
        for match in re.findall(pattern, text, flags=re.IGNORECASE):
            protected.append(match)

    temp_text = text

    for item in protected:
        temp_text = temp_text.replace(item, " ")

    simple_quantity_pattern = r"\d+(?:[,.]\d+)?(?:kg|g|dkg|l|ml|db|darab|csomag)"
    simple_quantities = re.findall(simple_quantity_pattern, temp_text, flags=re.IGNORECASE)

    temp_text = re.sub(simple_quantity_pattern, " ", temp_text, flags=re.IGNORECASE)
    temp_text = re.sub(r"\s+", " ", temp_text).strip()

    if temp_text:
        words = temp_text.split()
        buffer = []

        split_words = [
            "csomagolt",
            "lédig",
            "gyorsfagyasztott",
            "többféle",
            "szeletelt",
            "frissen",
            "sütve"
        ]

        for word in words:
            if word.lower() in split_words:
                if buffer:
                    parts.append(" ".join(buffer))
                    buffer = []

                if word.lower() == "frissen":
                    buffer.append(word)
                elif buffer and buffer[-1].lower() == "frissen" and word.lower() == "sütve":
                    parts.append("frissen sütve")
                    buffer = []
                else:
                    parts.append(word)
            else:
                buffer.append(word)

        if buffer:
            parts.append(" ".join(buffer))

    parts.extend(protected)
    parts.extend(simple_quantities)

    return parts


def is_discount_or_promo_text(text):
    lower = text.lower()

    promo_patterns = [
        "vásárlása esetén",
        "minden második",
        "termék ára",
        "fizet",
        "kap",
        "legalább",
        "kedvezmény",
    ]

    return any(pattern in lower for pattern in promo_patterns)


def clean_parentheses_item(text):
    text = normalize_text(text)
    text = text.strip()

    # +visszaváltási díj: 50Ft -> visszaváltási díj: 50Ft
    text = re.sub(r"^\+\s*", "", text)

    return text


def clean_text_item(text):
    text = str(text).strip()
    lower = text.lower()

    removable_phrases = [
        r"\ba\s+kiszolgálópultban\b",
        r"\bkiszolgálópultban\b",
        r"\baz\s+önkiszolgálópultban\b",
        r"\bönkiszolgálópultban\b",
        r"\bcsemegepultban kapható\b",
        r"\bhúspultban kapható\b",
        r"\bhalpultban csomagoltan kapható\b",
        r"\bsajtpultban\b",
        r"\bönkiszolgáló részlegen kapható\b",
    ]

    for pattern in removable_phrases:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    text = re.sub(r"\s+", " ", text).strip(" ,.;")
    lower = text.lower()

    if lower in ["válogatás", "különböző", "részlegen", "kapható"]:
        return ""

    if re.match(r"^/[a-záéíóöőúüű]+$", lower):
        return ""

    if re.match(r"^\d+ft/$", lower):
        return ""

    return text


def split_description(text):
    text = normalize_text(text)

    if not text:
        return []

    # Akcióleírást nem darabolunk
    if "," in text or is_discount_or_promo_text(text):
        item = clean_text_item(text)
        return [item] if item else []

    result = []

    # 1. zárójelek kiszedése
    main_text, parentheses = extract_parentheses(text)

    # 2. fő szöveg darabolása biztonságos / mentén
    slash_parts = split_by_safe_slash(main_text)

    for part in slash_parts:
        part = part.strip(" ,.;")
        if not part:
            continue

        # 3. mennyiség + szöveg további bontása
        subparts = split_mixed_quantity_text(part)

        for subpart in subparts:
            subpart = subpart.strip(" ,.;")
            if subpart:
                result.append(subpart)

    # 4. zárójeles részek külön elemként visszarakva
    for item in parentheses:
        item = clean_parentheses_item(item)
        if item:
            result.append(item)

    # 5. zajszűrés + duplikációk kiszedése sorrend megtartásával
    cleaned = []
    seen = set()

    for item in result:
        item = clean_text_item(item)

        if not item:
            continue

        key = item.lower()
        if key not in seen:
            cleaned.append(item)
            seen.add(key)

    return cleaned


def merge_split_deposit_output_rows(rows):
    merged_rows = []
    used_indexes = set()

    for i, current in enumerate(rows):
        if i in used_indexes:
            continue

        current_text = str(current["darabolt_ertek"]).strip().lower()

        if "visszaváltási díj" in current_text:
            for j in range(i + 1, len(rows)):
                next_row = rows[j]

                same_product = current.get("egyedi_hash") == next_row.get("egyedi_hash")

                if not same_product:
                    break

                next_text = str(next_row["darabolt_ertek"]).strip()

                is_fee_value = re.fullmatch(
                    r"\+?\s*\d+(?:[,.]\d+)?\s*ft(?:/\s*(db|darab))?",
                    next_text.lower()
                )

                if is_fee_value:
                    new_row = current.copy()

                    base_text = str(current["darabolt_ertek"]).strip()

                    # + jel eltávolítása az elejéről
                    base_text = re.sub(r"^\+\s*", "", base_text)

                    new_row["darabolt_ertek"] = (
                        base_text.rstrip(":")
                        + ": "
                        + next_text
)
                    merged_rows.append(new_row)
                    used_indexes.add(j)
                    break
            else:
                merged_rows.append(current)

            continue

        merged_rows.append(current)

    return merged_rows


def main():
    df = pd.read_csv(INPUT_FILE, encoding="utf-8")

    rows = []

    for index, row in df.iterrows():
        parts = split_description(row["ertek"])

        for sorszam, part in enumerate(parts, start=1):
            rows.append({
                "darabolt_ertek": part,
                "egyedi_hash": row["egyedi_hash"]
            })

    rows = merge_split_deposit_output_rows(rows)
    out_df = pd.DataFrame(rows)
    out_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print(f"Kész: {OUTPUT_FILE}")
    print(f"Eredeti sorok száma: {len(df)}")
    print(f"Darabolt sorok száma: {len(out_df)}")


if __name__ == "__main__":
    main()