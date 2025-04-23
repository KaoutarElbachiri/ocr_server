import pytesseract
import cv2
import re
from fuzzywuzzy import fuzz
import pandas as pd
import unicodedata
import csv
import os

def ocr_image(path):
    image = cv2.imread(path)
    image = cv2.resize(image, None, fx=1.7, fy=1.7)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 11, 17, 17)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    text = pytesseract.image_to_string(thresh, lang='fra')
    return text

def normalize(text):
    # Enlève accents, met en minuscules, enlève caractères spéciaux
    nfkd_form = unicodedata.normalize('NFKD', text)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).lower()

def extract_amount(text):
    lines = text.split('\n')
    montant = None

    keywords = ["total a payer", "total à payer", "total transaction", "montant"]
    
    for i, line in enumerate(lines):
        line_clean = line.lower()
        if any(k in line_clean for k in keywords):
            # Cherche un montant sur cette ligne ou dans les 3 lignes suivantes
            for j in range(i, min(i+4, len(lines))):
                matches = re.findall(r'(\d+[.,]\d{2})', lines[j])
                if matches:
                    montant = matches[-1]
                    return montant  # trouvé → on sort

    # Fallback : chercher dans les 6 dernières lignes
    for line in reversed(lines[-6:]):
        matches = re.findall(r'(\d+[.,]\d{2})', line)
        if matches:
            montant = matches[-1]
            break

    return montant


def extract_date(text):
    match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text)
    return match.group(1) if match else None

def extract_shop_name(text):
    # Lire les commerces connus depuis le CSV
    try:
        df = pd.read_csv("commerces.csv")
        known_shops = [normalize(shop) for shop in df['nom'].dropna()]
    except Exception as e:
        print("Erreur lecture commerces.csv :", e)
        known_shops = []

    lines = text.strip().split('\n')
    best_score = 0
    corrected_name = "inconnu"

    for line in lines[:10]:
        line_clean = normalize(line.strip())
        if len(line_clean) < 5:
            continue

        for shop in known_shops:
            score = fuzz.partial_ratio(shop, line_clean)
            if score > best_score and score >= 70:
                best_score = score
                corrected_name = shop

    return corrected_name.upper()

def get_category(commerce):
    commerce = commerce.lower()
    cat_file = "categories.csv"
    if os.path.exists(cat_file):
        with open(cat_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['commerce'].strip().lower() == commerce:
                    return row['categorie']
    
    # Si non trouvé, on demande à l'utilisateur
    print(f"\nNouvel établissement détecté : {commerce}")
    print("Catégories possibles : alimentaire, vestimentaire, loisir, autre")
    return "inconnu"

    # On ajoute à categories.csv pour la prochaine fois
    with open(cat_file, 'a', newline='') as f:
        writer = csv.writer(f)
        if os.stat(cat_file).st_size == 0:
            writer.writerow(['commerce', 'categorie'])
        writer.writerow([commerce, categorie])
    
    return categorie

def save_ticket(date, commerce, montant, categorie):
    fichier = "tickets.csv"
    file_exists = os.path.exists(fichier)

    with open(fichier, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists or os.stat(fichier).st_size == 0:
            writer.writerow(['date', 'commerce', 'montant', 'catégorie'])
        writer.writerow([date, commerce, montant, categorie])

def analyse_ticket_from_image_file(filepath):
    text = ocr_image(filepath)
    commerce = extract_shop_name(text)
    montant = extract_amount(text)
    date = extract_date(text)
    categorie = get_category(commerce)
    return {
        "commerce": commerce,
        "montant": montant,
        "date": date,
        "categorie": categorie
    }


if __name__ == "__main__":
    path = "ticket.jpg"
    text = ocr_image(path)

    print("\n=== TEXTE OCR ===\n")
    print(text)

    print("\n=== INFOS EXTRACTEES ===")
    print("Commerce :", extract_shop_name(text))
    print("Montant  :", extract_amount(text))
    print("Date     :", extract_date(text))
    
    commerce = extract_shop_name(text)
    montant = extract_amount(text)
    date = extract_date(text)
    categorie = get_category(commerce)

    save_ticket(date, commerce, montant, categorie)

    print("\nTicket sauvegardé dans tickets.csv ✅")
