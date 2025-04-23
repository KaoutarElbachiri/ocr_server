from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import shutil
import uuid
import os
from ocr_utils import analyse_ticket_from_image_file
from fastapi import Form
from ocr_utils import save_ticket, normalize
import csv

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
def get_tickets():
    tickets = []
    try:
        with open("tickets.csv", "r") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                row["id"] = i  # on garde l'index réel
                tickets.append(row)
    except Exception as e:
        print("Erreur lecture tickets.csv :", e)

    return list(reversed(tickets))  # on retourne tous les tickets, du plus récent au plus ancien


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

