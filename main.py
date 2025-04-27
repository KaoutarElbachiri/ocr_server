from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import shutil
import uuid
import os
from ocr_utils import analyse_ticket_from_image_file
from fastapi import Form
from ocr_utils import save_ticket, normalize
import csv
from auth import creer_utilisateur, verifier_utilisateur
from fastapi import Body
from auth import creer_utilisateur, verifier_utilisateur
from fastapi.responses import StreamingResponse
import io
from fastapi import UploadFile, File, Form, Body
import csv
import smtplib
from email.message import EmailMessage
from fastapi import Query

# Utilisé pour enregistrer le fichier temporaire
import tempfile

app = FastAPI()

# Permettre les requêtes depuis ton appli Expo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tu peux restreindre plus tard
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.post("/analyser_ticket/")
async def analyser_ticket(image: UploadFile = File(...)):
    ext = image.filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    infos = analyse_ticket_from_image_file(file_path)
    return infos

@app.post("/valider_ticket/")
async def valider_ticket(
    commerce: str = Form(...),
    montant: str = Form(...),
    date: str = Form(...),
    categorie: str = Form(...)
):
    from ocr_utils import save_ticket
    save_ticket(date, normalize(commerce), montant, normalize(categorie))
    return {"status": "ok", "message": "Ticket enregistré avec succès"}

@app.get("/tickets")
def get_tickets(username: str = Query(...)):
    tickets = []
    try:
        with open("tickets.csv", "r") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if row.get("username") == username:  # 🔥 On filtre ici !
                    row["id"] = i
                    tickets.append(row)
    except Exception as e:
        print("Erreur lecture tickets.csv :", e)

    return list(reversed(tickets))

from pydantic import BaseModel
from fastapi import Body

class TicketIndex(BaseModel):
    index: int

@app.post("/supprimer_ticket/")
def supprimer_ticket(payload: TicketIndex):
    index = payload.index
    try:
        with open("tickets.csv", "r") as f:
            lines = f.readlines()

        header = lines[0]
        data = lines[1:]

        if index < 0 or index >= len(data):
            return {"status": "error", "message": "Index invalide"}

        del data[index]

        with open("tickets.csv", "w") as f:
            f.write(header)
            f.writelines(data)

        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/ajouter_commerce/")
def ajouter_commerce(nom: str = Form(...)):
    try:
        nom_normalisé = normalize(nom)
        with open("commerces.csv", "a", newline='') as f:
            writer = csv.writer(f)
            if os.stat("commerces.csv").st_size == 0:
                writer.writerow(['nom'])
            writer.writerow([nom_normalisé])
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/commerces")
def get_commerces():
    try:
        with open("commerces.csv", "r") as f:
            reader = csv.DictReader(f)
            return list(reader)
    except:
        return []

@app.post("/inscription")
def inscription(data: dict = Body(...)):
    username = data.get("username")
    mot_de_passe = data.get("mot_de_passe")
    ok, message = creer_utilisateur(username, mot_de_passe)
    return {"ok": ok, "message": message}

@app.post("/connexion")
def connexion(data: dict = Body(...)):
    username = data.get("username")
    mot_de_passe = data.get("mot_de_passe")
    ok, role = verifier_utilisateur(username, mot_de_passe)
    if ok:
        return {"ok": True, "role": role}
    else:
        return {"ok": False, "message": "Identifiants invalides"}


@app.post("/supprimer_compte")
def supprimer_compte(data: dict):
    username = data.get("username")
    if not username:
        return {"ok": False, "message": "Nom d'utilisateur manquant."}

    # Supprimer l'utilisateur
    try:
        from auth import supprimer_utilisateur
        success = supprimer_utilisateur(username)
        if success:
            return {"ok": True, "message": "Compte supprimé."}
        else:
            return {"ok": False, "message": "Utilisateur non trouvé."}
    except Exception as e:
        return {"ok": False, "message": str(e)}

@app.post("/reset_users")
def reset_users():
    try:
        with open("users.csv", "w", newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=["username", "password", "role"])
            writer.writeheader()  # Écrit juste l'en-tête sans aucun utilisateur
        return {"ok": True, "message": "Fichier users.csv réinitialisé."}
    except Exception as e:
        return {"ok": False, "message": str(e)}


@app.get("/users")
def get_users():
    users = []
    try:
        with open("users.csv", "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                users.append({
                    "username": row["username"],
                    "role": row["role"]
                })
    except Exception as e:
        print("Erreur lecture users.csv:", e)

    return users

# Exporter les données d'un utilisateur (téléchargement CSV)
@app.get("/exporter_donnees")
def exporter_donnees(username: str):
    try:
        tickets = []
        with open("tickets.csv", "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["username"] == username:
                    tickets.append(row)

        if not tickets:
            return {"status": "error", "message": "Aucune donnée trouvée."}

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=tickets[0].keys())
        writer.writeheader()
        writer.writerows(tickets)

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={username}_depenses.csv"}
        )
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Supprimer toutes les dépenses d'un utilisateur
@app.post("/delete_tickets")
def delete_tickets(data: dict):
    username = data.get("username")
    if not username:
        return {"ok": False, "message": "Nom d'utilisateur manquant"}

    try:
        with open("tickets.csv", "r") as f:
            lines = f.readlines()

        header = lines[0]
        data_lines = lines[1:]

        new_data = []
        for line in data_lines:
            if username not in line:
                new_data.append(line)

        with open("tickets.csv", "w") as f:
            f.write(header)
            f.writelines(new_data)

        return {"ok": True, "message": "Tickets supprimés avec succès"}
    except Exception as e:
        print("Erreur suppression tickets :", e)
        return {"ok": False, "message": "Erreur serveur"}


