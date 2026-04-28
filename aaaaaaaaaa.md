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