# Security Configuration Guide

## Database Credentials

This application requires PostgreSQL database credentials to be configured through environment variables for security.

### Required Environment Variables

Create a `.env` file in the project root (copy from `.env.example`):

```bash
cp .env.example .env
```

Then edit `.env` and set your secure database password:

```env
POSTGRES_PASSWORD=your_secure_password_here
```

### Security Best Practices

1. **Never commit credentials**: The `.env` file is gitignored and should never be committed
2. **Use strong passwords**: Generate secure passwords for production environments
3. **Rotate credentials regularly**: Update passwords periodically
4. **Limit access**: Use database user permissions to limit access scope
5. **Use secrets management**: In production, consider using:
   - Docker secrets
   - Kubernetes secrets
   - AWS Secrets Manager
   - HashiCorp Vault

### Environment Variable Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `POSTGRES_HOST` | PostgreSQL host address | `192.168.68.88` | No |
| `POSTGRES_PORT` | PostgreSQL port | `5432` | No |
| `POSTGRES_DB` | Database name | `inventory_system` | No |
| `POSTGRES_USER` | Database username | `postgres` | No |
| `POSTGRES_PASSWORD` | Database password | None | **Yes** |

### Docker Configuration

When using Docker, pass environment variables through:

1. **Docker Compose** (recommended for development):
   ```yaml
   services:
     backend:
       env_file:
         - .env
   ```

2. **Docker Run**:
   ```bash
   docker run --env-file .env myapp
   ```

3. **Docker Secrets** (recommended for production):
   ```yaml
   services:
     backend:
       secrets:
         - postgres_password
       environment:
         POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
   ```

### Troubleshooting

If you get an error about missing `POSTGRES_PASSWORD`:

1. Ensure `.env` file exists in the project root
2. Verify the password is set correctly
3. Check that your application is loading the `.env` file
4. For development, ensure you're using `poetry run` or activating the virtual environment

### Migration from Hardcoded Credentials

Previously, the database password was hardcoded in `backend/app/database/config.py`. This has been removed for security. If you're upgrading:

1. Create a `.env` file from `.env.example`
2. Set `POSTGRES_PASSWORD` to your database password
3. Restart your application

The application will now fail to start without proper environment configuration, preventing accidental deployment with default credentials.