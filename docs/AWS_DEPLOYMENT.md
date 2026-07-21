# CI/CD de backend FastAPI en AWS

El CI usa Python 3.12 y `requirements-dev.txt`. Ejecuta Ruff, Pytest, crea la
tabla de historial en SQLite y comprueba el arranque de FastAPI con
Gunicorn/Uvicorn. La base de datos de CI es un archivo temporal; no usa datos
ni credenciales externas.

Tras un CI exitoso en `main`, el deploy descarga exactamente el ZIP validado,
lo almacena en S3, crea o reutiliza una versión de Elastic Beanstalk y actualiza
el entorno. GitHub se autentica por OIDC, sin claves de acceso permanentes.

## Contrato del paquete

Elastic Beanstalk usa Python 3.12 sobre Amazon Linux 2023. El paquete debe
contener, en su raíz, `requirements.txt`, `Procfile` y `app/main.py`. El
`Procfile` ejecuta Gunicorn con el worker de Uvicorn sobre `app.main:app`.

El pipeline excluye control de versiones, entornos virtuales, pruebas, archivos
`.env` y artefactos temporales. Las configuraciones de Elastic Beanstalk como
`.ebextensions/` o `.platform/` se incluyen si se agregan posteriormente.

## Configuración de AWS

Antes del primer deploy, crea una aplicación y un entorno de Elastic Beanstalk
con la plataforma Python 3.12 AL2023, además de un bucket S3 privado para las
versiones. El bucket y el entorno deben estar en la misma región.

Crea un proveedor OIDC con emisor
`https://token.actions.githubusercontent.com` y audiencia `sts.amazonaws.com`.
El rol de GitHub debe restringirse al entorno `production` del repositorio:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Federated": "arn:aws:iam::<AWS_ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com" },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
        "token.actions.githubusercontent.com:sub": "repo:Alex-20KD/Buildathon2-Backend:environment:production"
      }
    }
  }]
}
```

La política de permisos mínima para el rol es:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::<DEPLOYMENT_BUCKET>"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:::<DEPLOYMENT_BUCKET>/elastic-beanstalk/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "elasticbeanstalk:CreateApplicationVersion",
        "elasticbeanstalk:UpdateEnvironment",
        "elasticbeanstalk:DescribeApplicationVersions",
        "elasticbeanstalk:DescribeEnvironments",
        "elasticbeanstalk:DescribeEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

En GitHub, crea el entorno `production`, añade el secreto
`AWS_DEPLOY_ROLE_ARN` y define estas variables:

| Variable | Ejemplo |
| --- | --- |
| `AWS_REGION` | `us-east-1` |
| `ELASTIC_BEANSTALK_APPLICATION` | `portoasiste-backend` |
| `ELASTIC_BEANSTALK_ENVIRONMENT` | `portoasiste-backend-prod` |
| `DEPLOYMENT_BUCKET` | `portoasiste-eb-versions-prod` |
