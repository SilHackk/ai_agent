# Diegimo instrukcija — Hetzner VPS

## 1. Hetzner serverio sukūrimas

1. Eik į https://hetzner.com → Cloud → Projects → Create Project
2. Spusk "Add Server":
   - Location: Helsinki arba Nuremberg (arčiau Lietuvos)
   - Image: **Ubuntu 24.04**
   - Type: **CX22** (2 CPU, 4GB RAM) — ~4.35€/mėn
   - SSH Key: pridėk savo SSH raktą (arba naudok slaptažodį)
3. Spusk "Create & Buy"
4. Gausi serverio IP adresą, pvz. `65.21.xxx.xxx`

---

## 2. Prisijungimas prie serverio

```bash
ssh root@65.21.xxx.xxx
```

---

## 3. Docker instaliavimas

```bash
apt-get update
apt-get install -y docker.io docker-compose-plugin git
systemctl start docker
systemctl enable docker
```

---

## 4. Projekto įkėlimas į serverį

**Variantas A — per Git (rekomenduojama):**
```bash
git clone https://github.com/TAVO_VARTOTOJAS/TAVO_PROJEKTAS.git
cd TAVO_PROJEKTAS
```

**Variantas B — per SCP (jei nėra GitHub):**
Savo kompiuteryje paleisk:
```bash
scp -r /kelias/iki/projekto root@65.21.xxx.xxx:/root/ai_langai
```
Tada serveryje:
```bash
cd /root/ai_langai
```

---

## 5. Aplinkos kintamųjų nustatymas

Serveryje sukurk `.env.local` failą:

```bash
nano .env.local
```

Įrašyk:
```env
OPENAI_API_KEY=sk-...
AZURE_CLIENT_ID=...
AZURE_CLIENT_SECRET=...
AZURE_TENANT_ID=...
AZURE_REDIRECT_URI=http://65.21.xxx.xxx/auth/callback
OUTLOOK_USER_EMAIL=vardas@imone.lt
APP_PASSWORD=stiprus_slaptazodis_cia
```

Išsaugok: `Ctrl+X` → `Y` → `Enter`

---

## 6. Paleisti aplikaciją

```bash
docker compose up -d --build
```

Palaukti ~3-5 minutes kol suinstaliuos viską.

Patikrinti ar veikia:
```bash
docker compose ps
docker compose logs -f
```

---

## 7. Atidaryti naršyklėje

```
http://65.21.xxx.xxx
```

Įvesti slaptažodį kurį nustatei `APP_PASSWORD`.

---

## 8. Klientui siųsti

Klientui pakanka išsiųsti tik:

```
Sveiki,

Jūsų AI langų užklausų asistentas prieinamas čia:
http://65.21.xxx.xxx

Slaptažodis: [nurodytas slaptažodis]

Rekomenduojama naršyklė: Google Chrome arba Edge.
```

---

## Naudingos komandos (serverio priežiūrai)

```bash
# Perkrauti po kodo pakeitimų
docker compose down && docker compose up -d --build

# Žiūrėti logus
docker compose logs -f

# Sustabdyti
docker compose down

# Patikrinti ar veikia
docker compose ps

# Duomenų bazės backup
cp /root/ai_langai/data/ai_agent.db /root/backup_$(date +%Y%m%d).db
```

---

## Automatinis backup (rekomenduojama)

```bash
crontab -e
```

Pridėk eilutę (backup kiekvieną dieną 3:00):
```
0 3 * * * cp /root/ai_langai/data/ai_agent.db /root/backups/ai_agent_$(date +\%Y\%m\%d).db
```

---

## Domeno nustatymas (nebūtina, bet geriau)

Jei turi domeną, pvz. `asistentas.imone.lt`:

1. DNS nustatymuose pridėk A įrašą:
   - Name: `asistentas`
   - Value: `65.21.xxx.xxx`

2. Palaukti ~10-30 min kol DNS atsinaujina

3. Klientui siųsi: `http://asistentas.imone.lt`

---

## Serverio atnaujinimas po kodo pakeitimų

```bash
# Jei naudoji Git
cd /root/ai_langai
git pull
docker compose down && docker compose up -d --build

# Jei kopijuoji failus rankiniu būdu
scp -r /kelias/projektas root@65.21.xxx.xxx:/root/ai_langai
ssh root@65.21.xxx.xxx "cd /root/ai_langai && docker compose down && docker compose up -d --build"
```