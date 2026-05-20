1 Pasiulymas

app/
    services/ - biznio logika ir ne tik. 
    routers/  - endpointai POST GET UPDATE DELETE
    models/   - DB modeliai
    schemas/  - validacija
    main.py   - entry point


2 .gitignore .env.local

uvicorn main:app --reload

atsidarai
http://127.0.0.1:8000/docs

Ten Swagger’e matysi endpoint’ą:
POST /analyze


UI jau turi idėją apie žmogaus vertinimą, bet saugojimas dar nėra pilnai sutvarkytas.

„Per artimiausią savaitę planuoju sutvarkyti analizės rezultatų išsaugojimą, pridėti klasikinį NLP pipeline su struktūrizuotų duomenų ištraukimu, pvz. kiekiai, matmenys, miestai, RAL spalvos, langų žymėjimai, ir pagerinti PDF analizę. Taip pat galiu pridėti aiškesnę darbuotojo suvestinę MBcad / Klaes darbui: ką reikia braižyti, kokių duomenų trūksta ir kokį atsakymą siųsti klientui.“

.\.venv\Scripts\Activate.ps1
http://localhost:8000/auth/callback
streamlit run streamlit.py
python -m uvicorn app.main:app --reload



Problema

„Langų gamybos įmonės gauna daug ne-struktūrizuotų klientų užklausų el. paštu ir PDF formatu. Darbuotojai rankiniu būdu ieško matmenų, kiekių, spalvų ir kitų parametrų prieš dirbdami su MBcad/Klaes.“

Tikslas

„Projekto tikslas — automatizuoti klientų laiškų ir PDF analizę naudojant klasikinius NLP metodus ir LLM.“

Kodėl ne vien GPT

Čia labai svarbu:

„Vien GPT naudojimo nepakanka, todėl prieš AI analizę naudojami klasikiniai NLP metodai:

teksto valymas,
tokenizacija,
stop words šalinimas,
regex šablonai,
raktažodžių leksikonai,
parametrų ištraukimas.“
Kodėl tai naudinga

„Tai sumažina informacinį triukšmą, leidžia tiksliau ištraukti techninius parametrus ir sumažina hallucination riziką.“

Projekte naudojamas hibridinis metodas: klasikiniai NLP metodai naudojami struktūrizuotų techninių parametrų ištraukimui, o LLM naudojamas platesnei kontekstinei analizei ir santraukų generavimui