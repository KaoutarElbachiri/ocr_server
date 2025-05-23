import csv
import os
import hashlib

USERS_FILE = "users.csv"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def creer_utilisateur(username, mot_de_passe):
    if not username or not mot_de_passe:
        return False, "Champs obligatoires"

    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row["username"] == username:
                    return False, "Nom d'utilisateur déjà pris"

    with open(USERS_FILE, 'a', newline='') as csvfile:
        fieldnames = ['username', 'password', 'role']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if os.stat(USERS_FILE).st_size == 0:
            writer.writeheader()

        role = "admin" if username.lower() == "kaoutar" else "user"
        writer.writerow({'username': username, 'password': hash_password(mot_de_passe), 'role': role})

    return True, "Utilisateur créé"

def verifier_utilisateur(username, mot_de_passe):
    if not os.path.exists(USERS_FILE):
        return False, None

    with open(USERS_FILE, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row["username"] == username and row["password"] == hash_password(mot_de_passe):
                return True, row["role"]

    return False, None


def supprimer_utilisateur(username):
    path = "users.csv"
    if not os.path.exists(path):
        return False

    lignes = []
    found = False
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["username"] != username:
                lignes.append(row)
            else:
                found = True

    if not found:
        return False

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["username", "password", "role"])
        writer.writeheader()
        writer.writerows(lignes)

    # (optionnel) Tu pourrais aussi supprimer son dossier foyer si tu veux
    return True

