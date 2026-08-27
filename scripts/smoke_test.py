import json
import uuid
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8010/api"
email = f"smoke_{uuid.uuid4().hex[:8]}@example.com"
password = "secret12"
results = []


def call(method, path, body=None, token=None, expect=200):
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            code = resp.status
            payload = json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        code = e.code
        try:
            payload = json.loads(raw) if raw else {"raw": raw}
        except Exception:
            payload = {"raw": raw}
    ok = code == expect or (isinstance(expect, (list, tuple)) and code in expect)
    results.append((ok, method, path, code, expect))
    print(("OK  " if ok else "FAIL"), method, path, "->", code, "expected", expect)
    if not ok:
        print("  body:", str(payload)[:300])
    return code, payload


print("email", email)
code, reg = call(
    "POST",
    "/auth/register",
    {
        "name": "Smoke Test",
        "email": email,
        "password": password,
        "password_confirmation": password,
    },
    expect=201,
)
token = (reg or {}).get("token") or ((reg or {}).get("data") or {}).get("token")
assert token, reg

call("GET", "/auth/user", token=token, expect=200)
code, login = call("POST", "/auth/login", {"email": email, "password": password}, expect=200)
token = (login or {}).get("token") or token

cv_body = {
    "templateId": "atlas",
    "title": "CV Smoke",
    "principal": True,
    "completion": 40,
    "identity": {
        "firstName": "Ada",
        "lastName": "Lovelace",
        "title": "Dev",
        "email": email,
        "phone": "",
        "location": "Douala",
    },
    "summary": "Ingenieur passionne par les systemes et les CV intelligents pour Nogalix application.",
    "experiences": [
        {
            "id": "e1",
            "title": "Dev",
            "company": "Nogalix",
            "start": "2024-01",
            "end": "",
            "current": True,
            "bullets": ["Creation API FastAPI"],
        }
    ],
    "education": [{"id": "ed1", "diploma": "Licence", "school": "Univ", "year": "2020"}],
    "skills": [
        {"id": "s1", "name": "Python", "level": 80},
        {"id": "s2", "name": "Next.js", "level": 70},
    ],
    "languages": [{"id": "l1", "name": "Francais", "level": "Natif"}],
    "projects": [],
    "certifications": [],
}
code, cv = call("POST", "/cv", cv_body, token=token, expect=200)
cv_id = (cv or {}).get("id")
assert cv_id, cv

call("GET", "/cv", token=token, expect=200)
call("GET", f"/cv/{cv_id}", token=token, expect=200)
call("POST", f"/cv/{cv_id}/analyse", token=token, expect=200)
call(
    "PUT",
    "/profile",
    {"name": "Ada Smoke", "email": email, "phone": "670000000", "location": "Yaounde"},
    token=token,
    expect=200,
)
code, notif = call("GET", "/notifications", token=token, expect=200)
assert "unread_notifications" in (notif or {}), notif
assert "read_notifications" in (notif or {}), notif

call(
    "POST",
    "/assistant/chat",
    {"message": "Quel modele choisir ?", "history": [], "zone": "vitrine"},
    expect=200,
)
call(
    "POST",
    "/assistant/chat",
    {"message": "Aide moi", "history": [], "zone": "app"},
    token=token,
    expect=200,
)
call(
    "POST",
    "/assistant/chat",
    {"message": "Aide moi", "history": [], "zone": "app"},
    expect=401,
)
call(
    "POST",
    "/contact",
    {"name": "Test", "email": email, "objet": "Question", "message": "Bonjour smoke test"},
    expect=200,
)
call("GET", "/templates", expect=200)
call("GET", "/health", expect=200)
call("GET", "/cv", expect=401)
call("DELETE", f"/cv/{cv_id}", token=token, expect=200)
call("POST", "/auth/logout", token=token, expect=200)

failed = [r for r in results if not r[0]]
print("\nSUMMARY", len(results) - len(failed), "/", len(results), "passed")
if failed:
    print("FAILED:", failed)
    raise SystemExit(1)
print("ALL GREEN")
