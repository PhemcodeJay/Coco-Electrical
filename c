services:
  - type: web
    name: coco-electrical
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn --config gunicorn.conf.py wsgi:app
    pythonVersion: "3.11"
    envVars:
      - key: FLASK_ENV
        value: production
      - key: ADMIN_USERNAME
        value: admin
      - key: ADMIN_PASSWORD
        generateValue: true
      - key: SECRET_KEY
        generateValue: true
      - key: WHATSAPP_NUMBER
        value: "+2348033939180"
    disk:
      name: coco-data
      mountPath: /opt/render/project/src/instance