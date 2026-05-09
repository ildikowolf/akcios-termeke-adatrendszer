import csv
import hashlib
import re
import time
import random
import requests
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, parse_qs, urlencode
from datetime import datetime
from bs4 import BeautifulSoup, Tag
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    )
}

STORE_KEYWORDS = [
    "Tesco", "ALDI", "Lidl", "Auchan", "SPAR"
]

CARD_LABELS = [
    "Clubcarddal",
    "Lidl Plus alkalmazással",
    "Bizalomkártyával",
    "Supershop kártyával",
]

CARD_KEYWORDS = [
    "clubcard",
    "lidl plus",
    "bizalomkártyával",
    "supershop kártyával",
]

BASE_DIR = Path(__file__).resolve().parent


@dataclass
class CategoryRow:
    url: str
    category_name: str
    hierarchy_level: int
    c_value: int


@dataclass
class ProductRecord:
    bolt_neve: Optional[str]
    termek_neve: Optional[str]
    akcio_idotartama: Optional[str]
    leiras: Optional[str]
    eredeti_ar: Optional[int]
    kedvezmenyes_ar: Optional[int]
    kartyas_e: bool
    kartya_tipus: Optional[str]
    kategoria: str
    kategoria_kod: int
    hierarchiaszint: int
    egyedi_hash: str


def create_session():
    session = requests.Session()

    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
    )

    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(HEADERS)

    return session


SESSION = create_session()


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_c_value(url: str) -> int:
    params = parse_qs(urlparse(url).query)
    raw = params.get("c", [None])[0]
    if raw is None:
        raise ValueError(f"Nincs c paraméter az URL-ben: {url}")
    return int(raw)


def read_category_file(path: str) -> list[CategoryRow]:
    rows: list[CategoryRow] = []

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        _ = next(reader, None)

        for raw in reader:
            if not raw or len(raw) < 3:
                continue

            url = raw[0].strip()
            category_name = raw[1].strip()
            hierarchy_level = int(raw[2].strip())

            rows.append(
                CategoryRow(
                    url=url,
                    category_name=category_name,
                    hierarchy_level=hierarchy_level,
                    c_value=extract_c_value(url),
                )
            )

    return rows


def choose_leaf_categories(rows: list[CategoryRow]) -> list[CategoryRow]:
    """
    Csak levélkategóriákat választ:
    - 1-es szint soha nem célpont
    - 3-as szint mindig célpont
    - 2-es szint csak akkor célpont, ha nincs alatta 3-as gyerek
    Feltételezi, hogy a fájl hierarchikus sorrendben van.
    """
    targets: list[CategoryRow] = []
    n = len(rows)

    for i, row in enumerate(rows):
        if row.hierarchy_level == 1:
            continue

        if row.hierarchy_level == 3:
            targets.append(row)
            continue

        if row.hierarchy_level == 2:
            has_level3_child = False
            j = i + 1

            while j < n:
                nxt = rows[j]

                if nxt.hierarchy_level <= 2:
                    break

                if nxt.hierarchy_level == 3:
                    has_level3_child = True
                    break

                j += 1

            if not has_level3_child:
                targets.append(row)

    return targets


def build_page_url_from_category_url(category_url: str, page_number: int) -> str:
    parsed = urlparse(category_url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    params["o"] = [str(page_number)]

    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{urlencode(params, doseq=True)}"


def fetch_soup(url: str) -> Optional[BeautifulSoup]:
    try:
        response = SESSION.get(url, timeout=(10, 30))
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")

    except requests.exceptions.RequestException as e:
        print(f"HIBA: {url}")
        print(e)
        return None


def page_has_no_results(soup: BeautifulSoup) -> bool:
    text = soup.get_text(" ", strip=True)
    return "Nincs a keresésnek megfelelő találat" in text


def find_product_cards(soup: BeautifulSoup) -> list[Tag]:
    """
    Csak azokat a legkisebb blokkokat keresi, amik tényleg termékkártyák.
    """
    candidates: list[Tag] = []

    for tag in soup.find_all(["article", "div", "section"]):
        if not isinstance(tag, Tag):
            continue

        title = tag.find(["h6", "h5", "h4"])
        if not title:
            continue

        text = tag.get_text("\n", strip=True)
        if not text:
            continue

        has_date = bool(
            re.search(
                r"\d{4}\.\d{2}\.\d{2}\s*-\s*(?:\d{2}\.\d{2}|\d{4}\.\d{2}\.\d{2})",
                text
            )
        )
        has_price = "Ft" in text
        has_image = bool(tag.find("img"))

        if has_date and has_price and has_image:
            candidates.append(tag)

    # csak a legbelső találatokat tartjuk meg
    result: list[Tag] = []

    for tag in candidates:
        has_child_candidate = False

        for child in candidates:
            if child is tag:
                continue

            parent = child.parent
            while parent and isinstance(parent, Tag):
                if parent is tag:
                    has_child_candidate = True
                    break
                parent = parent.parent

            if has_child_candidate:
                break

        if not has_child_candidate:
            result.append(tag)

    return result


def parse_store_name(card: Tag) -> Optional[str]:
    for img in card.find_all("img"):
        attrs = " ".join([
            str(img.get("alt", "")),
            str(img.get("title", "")),
            str(img.get("aria-label", "")),
            str(img.get("src", "")),
        ])

        for store in STORE_KEYWORDS:
            if store.lower() in attrs.lower():
                return store

    text = card.get_text(" ", strip=True)
    for store in STORE_KEYWORDS:
        if store.lower() in text.lower():
            return store

    return None


def parse_product_name(card: Tag) -> Optional[str]:
    title = card.find(["h6", "h5", "h4"])
    if title:
        return normalize_whitespace(title.get_text(" ", strip=True))
    return None


def parse_date_range(text: str) -> Optional[str]:
    m = re.search(
        r"\d{4}\.\d{2}\.\d{2}\s*-\s*(?:\d{2}\.\d{2}|\d{4}\.\d{2}\.\d{2})",
        text
    )
    if m:
        return normalize_whitespace(m.group(0))
    return None


def parse_card_info(text: str) -> tuple[bool, Optional[str]]:
    lower = text.lower()

    for label in CARD_LABELS:
        if label.lower() in lower:
            return True, label

    if any(key in lower for key in CARD_KEYWORDS):
        return True, None

    return False, None


def parse_prices(card: Tag, text: str) -> tuple[Optional[int], Optional[int]]:
    original_price = None
    discounted_price = None

    # Eredeti ár: először áthúzott html elemből
    strike_tag = card.find(["s", "del", "strike"])
    if strike_tag:
        m = re.search(r"([\d\s]+)\s*Ft", strike_tag.get_text(" ", strip=True))
        if m:
            original_price = int(re.sub(r"\s+", "", m.group(1)))

    # Fallback: szöveges mintából
    if original_price is None:
        strike_match = re.search(r"~~\s*([\d\s]+)\s*Ft\s*~~", text)
        if strike_match:
            original_price = int(re.sub(r"\s+", "", strike_match.group(1)))

    # Minden Ft-os érték összegyűjtése
    money_matches = re.findall(r"(\d[\d\s]*)\s*Ft(?!\s*/)", text, flags=re.IGNORECASE)
    values = []

    for raw in money_matches:
        cleaned = re.sub(r"\s+", "", raw)
        if cleaned.isdigit():
            values.append(int(cleaned))

    if values:
        if original_price is not None:
            for value in reversed(values):
                if value != original_price:
                    discounted_price = value
                    break

            if discounted_price is None:
                discounted_price = values[-1]
        else:
            discounted_price = values[-1]
            if len(values) >= 2:
                original_price = values[-2]

    return original_price, discounted_price


def parse_description(card: Tag, product_name: Optional[str], date_range: Optional[str]) -> Optional[str]:
    text = card.get_text("\n", strip=True)
    lines = [normalize_whitespace(line) for line in text.splitlines() if normalize_whitespace(line)]

    if not lines:
        return None

    start_idx = 0
    end_idx = len(lines)

    # terméknév után
    if product_name:
        for i, line in enumerate(lines):
            if line == product_name:
                start_idx = i + 1
                break

    # dátum után
    if date_range:
        for i in range(start_idx, len(lines)):
            if date_range in lines[i]:
                start_idx = i + 1
                break

    desc_lines = []

    for i in range(start_idx, len(lines)):
        line = lines[i]

        # CSAK TISZTA ÁRÁLLAPOT ÁLLÍTJA LE
        if re.fullmatch(r"\d[\d\s]*\s*Ft\*?", line):
            break

        # kártya sorok vége
        if line.startswith("*"):
            break

        desc_lines.append(line)

    description = " | ".join(desc_lines).strip(" |")
    return description or None


def make_hash(
    store_name: Optional[str],
    product_name: Optional[str],
    date_range: Optional[str],
    discounted_price: Optional[int],
    category_code: int,
) -> str:
    raw = " | ".join([
        store_name or "",
        product_name or "",
        date_range or "",
        str(discounted_price or ""),
        str(category_code),
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def parse_card(card: Tag, category: CategoryRow) -> Optional[ProductRecord]:
    text = card.get_text("\n", strip=True)

    if not text or "Ft" not in text:
        return None

    store_name = parse_store_name(card)
    product_name = parse_product_name(card)
    date_range = parse_date_range(text)
    original_price, discounted_price = parse_prices(card, text)
    card_promo, card_type = parse_card_info(text)
    description = parse_description(card, product_name, date_range)

    if not product_name and not discounted_price:
        return None

    unique_hash = make_hash(
        store_name=store_name,
        product_name=product_name,
        date_range=date_range,
        discounted_price=discounted_price,
        category_code=category.c_value,
    )

    return ProductRecord(
        bolt_neve=store_name,
        termek_neve=product_name,
        akcio_idotartama=date_range,
        leiras=description,
        eredeti_ar=original_price,
        kedvezmenyes_ar=discounted_price,
        kartyas_e=card_promo,
        kartya_tipus=card_type,
        kategoria=category.category_name,
        kategoria_kod=category.c_value,
        hierarchiaszint=category.hierarchy_level,
        egyedi_hash=unique_hash,
    )


def scrape_category(category: CategoryRow) -> list[ProductRecord]:
    records: list[ProductRecord] = []
    seen = set()
    page = 1
    failures = 0

    while True:
        url = build_page_url_from_category_url(category.url, page)
        print(f"Letöltés: {url}")

        soup = fetch_soup(url)

        if soup is None:
            failures += 1

            if failures >= 2:
                print("Túl sok hiba, kategória kihagyva.")
                break

            print("Várakozás hiba után...")
            time.sleep(random.uniform(5, 8))
            page += 1
            continue

        failures = 0

        if page_has_no_results(soup):
            print("Nincs találat, kategória vége.")
            break

        cards = find_product_cards(soup)

        if not cards:
            print("Nincs több kártya.")
            break

        new_count = 0

        for card in cards:
            record = parse_card(card, category)

            if not record:
                continue

            if record.egyedi_hash in seen:
                continue

            seen.add(record.egyedi_hash)
            records.append(record)
            new_count += 1

        if new_count == 0:
            print("Nincs új adat.")
            break

        page += 1
        time.sleep(random.uniform(2, 4))

    return records


def save_records_to_csv(records: list[ProductRecord], output_file: str) -> None:
    if not records:
        print("Nincs menthető rekord.")
        return

    fieldnames = list(asdict(records[0]).keys())

    with open(output_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for record in records:
            writer.writerow(asdict(record))

    print(f"CSV mentve ide: {output_file}")


def main():
    category_file = BASE_DIR / "kategoria_meghatarozo.txt"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = BASE_DIR / f"akcios_termekek_{timestamp}.csv"

    all_rows = read_category_file(str(category_file))
    scrape_targets = choose_leaf_categories(all_rows)

    print(f"Kategóriafájl: {category_file}")
    print(f"Beolvasott kategóriasorok: {len(all_rows)}")
    print(f"Scrape célpontok száma: {len(scrape_targets)}")
    print("Scrape célpontok:")

    for row in scrape_targets:
        print(f"  c={row.c_value} | {row.category_name} | szint={row.hierarchy_level}")

    all_records: list[ProductRecord] = []
    global_hashes = set()

    for category in scrape_targets:
        category_records = scrape_category(category)

        for record in category_records:
            if record.egyedi_hash in global_hashes:
                continue

            global_hashes.add(record.egyedi_hash)
            all_records.append(record)

        time.sleep(random.uniform(1, 3))

    save_records_to_csv(all_records, str(output_file))
    print(f"Összes rekord: {len(all_records)}")


if __name__ == "__main__":
    main()