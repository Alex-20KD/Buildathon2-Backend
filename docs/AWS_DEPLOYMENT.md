# CI/CD de backend en AWS

El workflow de CI (`.github/workflows/ci.yml`) detecta Node.js, .NET, Maven,
Gradle o Python y ejecuta sus pasos de construcción y pruebas habituales. Si la
API usa otra tecnología, modifica ese workflow antes de integrar código.

`deploy-production.yml` empaqueta el código con el SHA del commit, almacena el
paquete en S3, crea una versión de Elastic Beanstalk y la aplica al entorno de
producción. Se activa automáticamente después de que el CI de un push a `main`
finaliza correctamente. No usa claves de acceso de larga duración: GitHub se
autentica mediante OpenID Connect (OIDC).

## Configuración inicial de AWS

Antes del primer deploy, crea una aplicación y entorno de Elastic Beanstalk con
la plataforma compatible con la API (Node.js, .NET, Java o Python), y un bucket
S3 privado para las versiones. El bucket debe estar en la misma región que el
entorno. Para la primera versión puedes subir un paquete desde la consola de
AWS; los siguientes despliegues los realizará este workflow.

Crea un proveedor OIDC de AWS con emisor
`https://token.actions.githubusercontent.com` y audiencia `sts.amazonaws.com`.
Después crea un rol para GitHub con una política de confianza limitada al
entorno `production` de este repositorio:

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

El rol requiere permisos limitados al bucket de versiones para `s3:PutObject`,
`s3:GetObject` y `s3:ListBucket`, y a la aplicación de Elastic Beanstalk para
`elasticbeanstalk:CreateApplicationVersion`,
`elasticbeanstalk:UpdateEnvironment`,
`elasticbeanstalk:DescribeEnvironments` y
`elasticbeanstalk:DescribeEvents`.

## Configuración en GitHub

En **Settings → Environments → production**, habilita las aprobaciones que
correspondan. Añade el secreto `AWS_DEPLOY_ROLE_ARN` con el ARN del rol OIDC.
En **Settings → Secrets and variables → Actions → Variables**, añade:

| Variable | Ejemplo |
| --- | --- |
| `AWS_REGION` | `us-east-1` |
| `ELASTIC_BEANSTALK_APPLICATION` | `buildathon-backend` |
| `ELASTIC_BEANSTALK_ENVIRONMENT` | `buildathon-backend-prod` |
| `DEPLOYMENT_BUCKET` | `buildathon-eb-versions-prod` |

El paquete excluye el control de versiones, dependencias locales y artefactos
temporales, pero conserva los archivos de configuración de Elastic Beanstalk
como `.ebextensions/`, `.platform/`, `Procfile` y `Dockerrun.aws.json`. Un push
a `main` se despliega solo si el CI acaba correctamente; también se puede lanzar
de forma manual desde la pestaña **Actions**.
