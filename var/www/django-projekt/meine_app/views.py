from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
import json


REPORTS_FILE = "/var/www/django-projekt/data/berichte.json"
USERS_FILE = "/var/www/django-projekt/data/users.json"
MODULE_FILE = "/var/www/django-projekt/data/module.json"
ROLE_REQUESTS_FILE = "/var/www/django-projekt/data/role_requests.json"



def ctx(request):
    return {
        "username": request.session.get("username"),
        "role": request.session.get("role"),
    }


def vip_or_admin(request):
    return request.session.get("role") in ["vip", "admin"]


# ================ CSV Export ==================
 
def export_csv(request):
   if not _check_vip_or_admin(request):
       return redirect("uebersicht")
   reports = _load_reports()
   user_email = request.session.get("email")
   eigene = [r for r in reports if r["user"] == user_email]
   response = HttpResponse(content_type="text/csv")						# HTTP Antwort als CSV definieren
   response["Content-Disposition"] = 'attachment; filename="berichte.csv"'			# Browser soll Download starten
   writer = csv.writer(response)								# CSV-Writer erstellen
   writer.writerow(["Datum", "Modul", "Minuten", "Beschreibung"])				# Kopfzeile schreiben
   for r in eigene:
       writer.writerow([
           r.get("datum"),
           r.get("modul"),
           r.get("minuten"),
           r.get("content")
       ])
   return response										# CSV Download zurueckgeben
 
# =============== XML Export ==================
 
def export_xml(request):
   if not _check_vip_or_admin(request):
       return redirect("uebersicht")
   reports = _load_reports()
   user_email = request.session.get("email")
   eigene = [r for r in reports if r["user"] == user_email]
   root = ET.Element("berichte")								# XML Root erstellen
   for r in eigene:										# Jeden Bericht als XML-Knoten anhaengen
       bericht = ET.SubElement(root, "bericht")
       ET.SubElement(bericht, "datum").text = r.get("datum", "")
       ET.SubElement(bericht, "modul").text = r.get("modul", "")
       ET.SubElement(bericht, "minuten").text = str(r.get("minuten", 0))
       ET.SubElement(bericht, "beschreibung").text = r.get("content", "")
   xml_data = ET.tostring(root, encoding="utf-8")						# XML in Bytes umwandeln
   response = HttpResponse(xml_data, content_type="application/xml")				# HTTP Antwort als XML senden
   response["Content-Disposition"] = 'attachment; filename="berichte.xml"'			# Browser soll Download starten
   return response
 


# LOGIN


def benutzer_login(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "").strip()
        role = request.POST.get("role")

        if not role:
            messages.error(request, "Bitte eine Rolle auswaehlen.")
            return render(request, "login.html")

        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                users = json.load(f)
        except:
            users = []

        user = None
        for u in users:
            if u.get("email", "").lower() == email:
                user = u
                break

        if not user or user.get("password") != password:
            messages.error(request, "Email oder Passwort ist falsch.")
            return render(request, "login.html")

        if user.get("is_active") is False:
            messages.error(request, "Dein Konto wurde gesperrt.")
            return render(request, "login.html")

        real_role = user.get("role", "simple")

        if real_role == "admin":
            erlaubt = role in ["admin", "vip", "simple"]
        elif real_role == "vip":
            erlaubt = role in ["vip", "simple"]
        else:
            erlaubt = role == "simple"

        if not erlaubt:
            messages.error(request, "Diese Rolle darfst du nicht verwenden.")
            return render(request, "login.html")

        request.session["username"] = user.get("username")
        request.session["email"] = user.get("email")
        request.session["role"] = role

        return redirect("uebersicht")

    return render(request, "login.html")


# REGISTRIEREN

def registrieren(request):
    if request.method == "POST":
        fname = (request.POST.get("vorname") or "").strip()
        lname = (request.POST.get("nachname") or "").strip()
        email = (request.POST.get("email") or "").strip().lower()
        password = (request.POST.get("password") or "").strip()

        if not fname or not lname or not email or not password:
            messages.error(request, "Bitte alle Felder ausfuellen.")
            return render(request, "registrieren.html")

        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                users = json.load(f)
        except:
            users = []

        for u in users:
            if u.get("email", "").lower() == email:
                messages.error(request, "Email bereits registriert.")
                return render(request, "registrieren.html")

        username = email.split("@")[0]
        users.append({
            "username": username,
            "first_name": fname,
            "last_name": lname,
            "email": email,
            "password": password,
            "role": "simple",
            "is_active": True
        })

        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)

        messages.success(request, "Registrierung erfolgreich. Bitte einloggen.")
        return redirect("login")

    return render(request, "registrieren.html")



# LOGOUT

def logout_view(request):
    request.session.flush()
    return redirect("login")



# SEITEN

def uebersicht(request):
    c = ctx(request)

    try:
        with open(REPORTS_FILE, "r", encoding="utf-8") as f:
            reports = json.load(f)
    except:
        reports = []

    email = request.session.get("email")
    eigene = [r for r in reports if r.get("user") == email]

    gesamt_minuten = sum(r.get("minuten", 0) for r in eigene)
    c["gesamt_minuten"] = gesamt_minuten
    c["gesamt_stunden"] = round(gesamt_minuten / 60, 2)

    # UeberSicht
    module_map = {}
    for r in eigene:
        m = r.get("modul", "Unbekannt")
        module_map[m] = module_map.get(m, 0) + r.get("minuten", 0)

    module_details = []
    for m, mins in module_map.items():
        module_details.append({
            "name": m,
            "minuten": mins,
            "stunden": round(mins / 60, 2)
        })
    c["module_details"] = module_details

    return render(request, "uebersicht.html", c)


def berichte(request):
    c = ctx(request)

    try:
        with open(MODULE_FILE, "r", encoding="utf-8") as f:
            modules = json.load(f)
    except:
        modules = ["SA"]
        with open(MODULE_FILE, "w", encoding="utf-8") as f:
            json.dump(modules, f, ensure_ascii=False, indent=2)

    c["modules"] = modules

    if request.method == "POST":
        try:
            with open(REPORTS_FILE, "r", encoding="utf-8") as f:
                reports = json.load(f)
        except:
            reports = []

        reports.append({
            "id": len(reports) + 1,
            "user": request.session.get("email"),
            "username": request.session.get("username"),
            "datum": request.POST.get("datum"),
            "modul": request.POST.get("modul"),
            "minuten": int(request.POST.get("minuten") or 0),
            "content": request.POST.get("content", ""),
        })

        with open(REPORTS_FILE, "w", encoding="utf-8") as f:
            json.dump(reports, f, ensure_ascii=False, indent=2)

        return redirect("meine_berichte")

    return render(request, "berichte.html", c)


def meine_berichte(request):
    c = ctx(request)

    try:
        with open(REPORTS_FILE, "r", encoding="utf-8") as f:
            reports = json.load(f)
    except:
        reports = []

    email = request.session.get("email")
    eigene = [r for r in reports if r.get("user") == email]

    c["berichte"] = eigene
    c["gesamt_minuten"] = sum(r.get("minuten", 0) for r in eigene)

    return render(request, "meine_berichte.html", c)


def bericht_loeschen(request, bericht_id):
    try:
        with open(REPORTS_FILE, "r", encoding="utf-8") as f:
            reports = json.load(f)
    except:
        reports = []

    email = request.session.get("email")
    reports = [r for r in reports if not (r.get("id") == bericht_id and r.get("user") == email)]

    with open(REPORTS_FILE, "w", encoding="utf-8") as f:
        json.dump(reports, f, ensure_ascii=False, indent=2)

    return redirect("meine_berichte")





# Bericht bearbeiten

def bericht_bearbeiten(request, bericht_id):
    
    try:
        with open(REPORTS_FILE, "r", encoding="utf-8") as f:
            reports = json.load(f)
    except:
        reports = []

    user_email = request.session.get("email")

    
    bericht = None
    for r in reports:
        if r.get("id") == bericht_id and r.get("user") == user_email:
            bericht = r
            break

    if not bericht:
        return redirect("meine_berichte")

   
    try:
        with open(MODULE_FILE, "r", encoding="utf-8") as f:
            modules = json.load(f)
    except:
        modules = ["SA"]

    if request.method == "POST":
        bericht["datum"] = request.POST.get("datum")
        bericht["modul"] = request.POST.get("modul")
        bericht["minuten"] = int(request.POST.get("minuten") or 0)
        bericht["content"] = request.POST.get("content", "")

        # speichern
        with open(REPORTS_FILE, "w", encoding="utf-8") as f:
            json.dump(reports, f, ensure_ascii=False, indent=2)

        return redirect("meine_berichte")

    return render(request, "berichte.html", {
        **ctx(request),
        "edit": True,
        "bericht": bericht,
        "modules": modules,
    })



# Rollenantrag

def einstellungen(request):
    c = ctx(request)

    
    try:
        with open(ROLE_REQUESTS_FILE, "r", encoding="utf-8") as f:
            reqs = json.load(f)
    except:
        reqs = []

    if request.method == "POST":
        zielrolle = request.POST.get("zielrolle")
        begruendung = request.POST.get("begruendung", "")

        reqs.append({
            "id": len(reqs) + 1,
            "username": request.session.get("username"),
            "email": request.session.get("email"),
            "current_role": request.session.get("role"),
            "requested_role": zielrolle,
            "reason": begruendung,
            "status": "offen",
        })

        with open(ROLE_REQUESTS_FILE, "w", encoding="utf-8") as f:
            json.dump(reqs, f, ensure_ascii=False, indent=2)

        return redirect("einstellungen")

    return render(request, "einstellungen.html", c)



# Rollenantraege ansehen

def rollen_antraege(request):
    role = request.session.get("role")
    if role != "admin":
        messages.error(request, "Kein Zugriff. Nur Administratoren duerfen dies sehen.")
        return redirect("uebersicht")

    try:
        with open(ROLE_REQUESTS_FILE, "r", encoding="utf-8") as f:
            role_requests = json.load(f)
    except:
        role_requests = []

    return render(request, "rollen_antraege.html", {
        "username": request.session.get("username"),
        "role": role,
        "role_requests": role_requests,
    })



# Rolle genehmigen

def rolle_genehmigen(request, request_id):
    if request.session.get("role") != "admin":
        return redirect("uebersicht")

    
    try:
        with open(ROLE_REQUESTS_FILE, "r", encoding="utf-8") as f:
            role_requests = json.load(f)
    except:
        role_requests = []

    
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
    except:
        users = []

    req = None
    for r in role_requests:
        if r.get("id") == request_id:
            req = r
            break

    if not req:
        messages.error(request, "Antrag nicht gefunden.")
        return redirect("rollen_antraege")

    
    for u in users:
        if u.get("email", "").lower() == (req.get("email", "").lower()):
            u["role"] = req.get("requested_role")
            break

    
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

    
    role_requests = [r for r in role_requests if r.get("id") != request_id]

    with open(ROLE_REQUESTS_FILE, "w", encoding="utf-8") as f:
        json.dump(role_requests, f, ensure_ascii=False, indent=2)

    return redirect("rollen_antraege")



def rolle_ablehnen(request, request_id):
    if request.session.get("role") != "admin":
        return redirect("uebersicht")

    try:
        with open(ROLE_REQUESTS_FILE, "r", encoding="utf-8") as f:
            role_requests = json.load(f)
    except:
        role_requests = []

    role_requests = [r for r in role_requests if r.get("id") != request_id]

    with open(ROLE_REQUESTS_FILE, "w", encoding="utf-8") as f:
        json.dump(role_requests, f, ensure_ascii=False, indent=2)

    return redirect("rollen_antraege")



# Module verwalten

def module_verwalten(request):
    if request.session.get("role") != "admin":
        return redirect("uebersicht")

    try:
        with open(MODULE_FILE, "r", encoding="utf-8") as f:
            modules = json.load(f)
    except:
        modules = ["SA"]

    if request.method == "POST":
        neues_modul = (request.POST.get("modul") or "").strip()
        if neues_modul and neues_modul not in modules:
            modules.append(neues_modul)

            with open(MODULE_FILE, "w", encoding="utf-8") as f:
                json.dump(modules, f, ensure_ascii=False, indent=2)

    return render(request, "module_verwalten.html", {
        **ctx(request),
        "modules": modules,
    })


def modul_loeschen(request, modul_name):
    if request.session.get("role") != "admin":
        return redirect("uebersicht")

    try:
        with open(MODULE_FILE, "r", encoding="utf-8") as f:
            modules = json.load(f)
    except:
        modules = ["SA"]

    if modul_name in modules:
        modules.remove(modul_name)

        with open(MODULE_FILE, "w", encoding="utf-8") as f:
            json.dump(modules, f, ensure_ascii=False, indent=2)

    return redirect("module_verwalten")



def benutzer_verwalten(request):
    if request.session.get("role") != "admin":
        return redirect("uebersicht")

    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
    except:
        users = []

    return render(request, "benutzer_verwalten.html", {
        "username": request.session.get("username"),
        "role": request.session.get("role"),
        "users": users,
    })


def benutzer_sperren(request, email):
    if request.session.get("role") != "admin":
        return redirect("uebersicht")

    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
    except:
        users = []

    admin_email = request.session.get("email")

    for u in users:
        if u.get("email") == email and u.get("email") != admin_email:
            u["is_active"] = False

    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

    return redirect("benutzer_verwalten")


def benutzer_entsperren(request, email):
    if request.session.get("role") != "admin":
        return redirect("uebersicht")

    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
    except:
        users = []

    for u in users:
        if u.get("email") == email:
            u["is_active"] = True

    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

    return redirect("benutzer_verwalten")

