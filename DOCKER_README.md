# Running This LMS With Docker

This guide is for someone who has never used Docker before. Follow the steps in order and you should be able to run the application locally.

## What Docker Does Here

Docker runs the app in small containers so you do not need to manually install PostgreSQL, system packages, or a production web server.

This project starts two main containers:

- `web`: the Django LMS application
- `db`: the PostgreSQL database

The application will be available at:

```text
http://localhost:8000
```

The admin panel will be available at:

```text
http://localhost:8000/admin
```

## 1. Install Docker Desktop

Install Docker Desktop for Windows:

```text
https://www.docker.com/products/docker-desktop/
```

After installing it:

1. Open Docker Desktop.
2. Wait until it says Docker is running.
3. Keep Docker Desktop open while using the app.

## 2. Open The Project Folder

Open PowerShell or Command Prompt in this folder:

```text
DockerLRSS
```

You can check that you are in the right folder by running:

```powershell
dir
```

You should see files like:

```text
docker-compose.yml
Dockerfile
manage.py
.env.docker
```

## 3. Start The Application

Run this command:

```powershell
docker compose --env-file .env.docker up --build
```

The first run can take a few minutes because Docker needs to download and build everything.

When it is ready, open:

```text
http://localhost:8000
```

To open the admin panel:

```text
http://localhost:8000/admin
```

## 4. Login To The Admin Panel

The Docker startup creates a default admin user:

```text
email: admin@example.com
password: admin123
```

Change this password before using the app for anything serious.

## 5. Create A New Superuser

If you want to create your own admin user, keep the containers running and open a second PowerShell window in the project folder.

Run:

```powershell
docker compose --env-file .env.docker exec web python manage.py createsuperuser
```

Follow the prompts.

## 6. Stop The Application

Press `Ctrl + C` in the terminal where Docker is running.

Then run:

```powershell
docker compose --env-file .env.docker down
```

This stops the containers but keeps the database data.

## 7. Start It Again Later

Next time, run:

```powershell
docker compose --env-file .env.docker up
```

If you changed code or dependencies, rebuild:

```powershell
docker compose --env-file .env.docker up --build
```

## Useful Commands

Show running containers:

```powershell
docker compose --env-file .env.docker ps
```

View app logs:

```powershell
docker compose --env-file .env.docker logs -f web
```

View database logs:

```powershell
docker compose --env-file .env.docker logs -f db
```

Run database migrations manually:

```powershell
docker compose --env-file .env.docker exec web python manage.py migrate
```

Open a Django shell:

```powershell
docker compose --env-file .env.docker exec web python manage.py shell
```

Open a database shell:

```powershell
docker compose --env-file .env.docker exec db psql -U lms_user -d lms_db
```

## If Port 8000 Is Already In Use

Edit `.env.docker` and change:

```text
WEB_PORT=8000
```

For example:

```text
WEB_PORT=8001
```

Then start again:

```powershell
docker compose --env-file .env.docker up --build
```

Open:

```text
http://localhost:8001
```

## Reset The Database

Only do this if you want to delete the local Docker database and start fresh.

Stop everything:

```powershell
docker compose --env-file .env.docker down
```

Delete the database volume:

```powershell
docker volume rm dockerlrss_postgres_data
```

Start again:

```powershell
docker compose --env-file .env.docker up --build
```

## Common Problems

### Docker says it cannot connect to the Docker engine

Open Docker Desktop and wait until it fully starts.

### The site does not open

Check the containers:

```powershell
docker compose --env-file .env.docker ps
```

Then check the web logs:

```powershell
docker compose --env-file .env.docker logs -f web
```

### The database says a database does not exist

Make sure you are using:

```powershell
docker compose --env-file .env.docker up --build
```

The app should connect to the `lms_db` database using the `lms_user` user.

### Docker says the port is already allocated

Another app is already using the port. Change `WEB_PORT` in `.env.docker`, or stop the other app.

## Quick Version

For daily use:

```powershell
docker compose --env-file .env.docker up
```

Open:

```text
http://localhost:8000
```

Stop:

```powershell
docker compose --env-file .env.docker down
```
