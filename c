# Render Deployment Configuration
# This file defines the infrastructure for Render deployment

services:
  - type: web
    name: coco-electrical
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn wsgi:app
    envVars:
      - key: FLASK_ENV
        value: production
      - key: ADMIN_USERNAME
        value: admin
        # Update this in Render dashboard for production
      - key: ADMIN_PASSWORD
        value: admin123
        # Update this in Render dashboard for production
      - key: SECRET_KEY
        value: your-secret-key-here
        # Update this in Render dashboard for production
      - key: WHATSAPP_NUMBER
        value: +2348033939180
    disk:
      name: coco-data
      mountPath: /opt/render/project/src/instance