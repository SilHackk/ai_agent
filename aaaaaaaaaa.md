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