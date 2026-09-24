# Savorly

Savorly is a responsive Django recipe-sharing web application built around a community of home cooks and approved chefs. It includes account registration, role-aware authentication, admin-managed chef approval, email notifications, and chef-only recipe management.

The project uses Django's built-in authentication and admin systems, SQLite for local data, server-rendered templates, Bootstrap 5, custom CSS, and a small amount of vanilla JavaScript.

## Features

### Public landing and navigation

- Responsive Savorly landing page with separate **User**, **Chef**, and **Admin** entry points.
- Shared navigation for Home, Recipe, and Chef's Table pages.
- Current-page highlighting in the navigation.
- Welcome message and CSRF-protected logout button for signed-in users.
- Responsive layout for desktop, tablet, and mobile screens.
- Semantic headings, labeled forms, keyboard focus styles, accessible error states, image alternative text, and an accessible table caption.
- Dismissible success, error, and informational messages.
- Custom Savorly branding, favicon, hero image, and theme.

### User accounts

- Immediate user registration through `/register/user/`.
- Optional email address for regular users.
- Password confirmation and Django password validation.
- Username validation, case-insensitive duplicate detection, and a 150-character limit.
- Automatic login after successful user registration.
- A one-to-one profile with the `User` role.
- Role-aware login and logout.
- Password show/hide controls.
- Safe internal `next` redirect handling after login.
- Approved chefs are sent to the recipe page after login; regular users return to the home page.
- Administrators and Django staff accounts are directed to the secure Django admin login instead of the public login.

### Chef applications and approval

- Chef registration through `/register/chef/`.
- Required, validated email address for chef applications.
- New chef accounts are created as inactive and remain unable to sign in until approval.
- Each application records its request time and current approval status.
- Public login explains when an application is pending, removed, inactive, or not yet approved.
- Admin approval activates the chef account and records the approving administrator and approval time.
- Approval email includes the chef's username and a role-specific sign-in link.
- Administrators can resend approval emails to approved chefs.
- Administrators can remove chef access, deactivate the account, and record the removal time and reviewer.
- Removed chefs can reapply with the same username; registration updates their email and password and returns the profile to pending status.
- Registration, reapplication, approval, and removal use database transactions to protect concurrent account changes.

### Chef administration

The Django admin is branded as **Savorly administration** and provides:

- Separate **User profiles** and **Chef profiles** views.
- User-profile filtering by account activity.
- Chef-profile filtering by approval status and account activity.
- Search by username, email, or first name.
- Approval timestamps and approving/removing administrator audit fields.
- Bulk actions to:
  - approve pending chef registrations,
  - resend approval emails, or
  - remove chef profiles.
- Email delivery failures reported to the administrator without rolling back a successful approval.
- Protection against manually adding or deleting profiles from these community profile admin pages.
- Removed chef profiles are hidden from the normal chef-profile list.

The model supports `Pending approval`, `Approved`, `Rejected`, and `Removed` states. The current admin actions implement approval, resend, and removal; there is no dedicated reject action.

### Recipe management

All recipe tools currently require an **approved chef** account.

- Add recipes with:
  - a required name of up to 100 characters,
  - a required full description, and
  - an optional uploaded image.
- Store uploaded images under `media/recipe_images/`.
- Automatically associate newly created recipes with the signed-in chef.
- Browse every submitted recipe on the Chef's Table, newest first.
- Show the total recipe count and provide an empty-state call to action.
- Preview descriptions to 30 words in the recipe table.
- View a recipe's complete description, image, and author on a dedicated details page.
- Graceful "No image" placeholders for recipes without an uploaded image.
- Update only recipes owned by the signed-in chef.
- Preserve an existing image when editing unless a replacement is submitted.
- Hide update and delete actions for other chefs' recipes.
- Prevent regular users and other non-chef accounts from accessing recipe management pages.
- Return helpful Django messages after recipe creation, updates, and deletion.
- Legacy route aliases are retained for Chef's Table and recipe update URLs.

### Email notifications

Chef approval emails are sent through Django's email framework.

- Gmail-compatible SMTP defaults are already configured.
- SMTP is selected automatically when `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` are present.
- Without SMTP credentials, email is safely printed to the server console.
- The public URL used in sign-in links is configurable.
- A Windows PowerShell helper securely prompts for a Gmail app password and stores the SMTP settings for the current Windows user.

### Health check

- `GET /health` returns HTTP 200 with:

```json
{"status": "ok"}
```

- Other HTTP methods are rejected.

## Technology

| Component | Technology |
| --- | --- |
| Backend | Django 6.1.1 |
| Language | Python 3.13 (verified locally) |
| Database | SQLite |
| Authentication | Django authentication and sessions |
| Admin | Django admin |
| Templates | Django templates |
| UI | Bootstrap 5.3.8 CDN, custom CSS, vanilla JavaScript |
| Fonts | Google Fonts: DM Sans and DM Serif Display |
| Images | Django `ImageField` with Pillow 12.3.0 (verified locally) |
| Email | Django SMTP/console email backends |

> The repository does not currently include a `requirements.txt` or `pyproject.toml`. Install the versions listed above, or compatible versions supported by your environment.

## Quick start

### 1. Prerequisites

Install:

- Python 3.13
- Django 6.1.1
- Pillow

Internet access is needed if you want the Google Fonts and Bootstrap assets loaded from their CDNs.

### 2. Create a virtual environment

From the project directory:

```powershell
cd D:\Savorly
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

On macOS/Linux, activate it with:

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install "Django==6.1.1" "Pillow==12.3.0"
```

### 4. Apply database migrations

```powershell
python manage.py migrate
```

The project uses the root-level `db.sqlite3` database. This database is already present in the repository and may contain existing data; back it up before applying migrations, and do not delete it unless you intend to reset the local database.

Two migrations also transform existing data: an earlier profile migration marks pre-existing chef profiles as approved, and the recipe-owner migration backfills legacy recipes only when exactly one chef profile can be identified.

### 5. Create an administrator

```powershell
python manage.py createsuperuser
```

This account signs in at `/admin/`. Administrator registration is intentionally unavailable through the public site.

### 6. Start the development server

```powershell
python manage.py runserver
```

Open <http://localhost:8000/>.

## Typical usage

### Register a regular user

1. Open the home page.
2. Select **User**.
3. Enter a username, optional email, and matching passwords.
4. Submit the form; the account is activated and signed in immediately.

### Register and approve a chef

1. Open the home page.
2. Select **Chef**.
3. Submit the application with a valid email address.
4. Sign in to `/admin/` as a superuser.
5. Open **Chef profiles**.
6. Select the pending chef and choose **Approve selected chef registrations**.
7. The account becomes active and the application attempts to send an approval email.
8. The chef can sign in from `/login/?role=chef` and is taken to `/recipes/`.

### Add a recipe

1. Sign in as an approved chef.
2. Open `/recipes/` or **Recipe** in the navigation.
3. Enter a recipe name and description, optionally attach an image, and submit.
4. Open **Chef's Table** to view all community recipes.
5. Use the owner's **Update** or **Delete** actions to manage the recipe.

## URL reference

| URL | Methods | Access | Purpose |
| --- | --- | --- | --- |
| `/` | GET | Public | Landing and account-type selection |
| `/register/user/` | GET, POST | Public | Register a regular user |
| `/register/chef/` | GET, POST | Public | Apply for chef access |
| `/login/` | GET, POST | Public | User/chef login |
| `/logout/` | POST | Signed in | Sign out |
| `/health` | GET | Public | JSON health check |
| `/recipes/` | GET, POST | Approved chef | Add a recipe |
| `/chefs-table/` | GET | Approved chef | Browse community recipes |
| `/recipes/<id>/` | GET | Approved chef | View recipe details |
| `/update_recipe/<id>/` | GET, POST | Owning chef | Edit a recipe |
| `/delete_recipe/<id>/` | GET | Owning chef | Delete a recipe |
| `/admin/` | Standard admin URLs | Staff/admin | Manage users, chefs, and applications |

Unauthenticated users who open a protected page are redirected to login. Signed-in non-chefs are redirected to the home page with an explanatory message.

## Email configuration

The project reads email settings directly from environment variables. It does not automatically load a `.env` file.

| Variable | Default | Description |
| --- | --- | --- |
| `EMAIL_HOST` | `smtp.gmail.com` | SMTP server |
| `EMAIL_PORT` | `587` | SMTP port |
| `EMAIL_HOST_USER` | Empty | SMTP account/email address |
| `EMAIL_HOST_PASSWORD` | Empty | SMTP password or app password |
| `EMAIL_USE_TLS` | `true` | Enables TLS; accepts `1`, `true`, or `yes` |
| `DJANGO_EMAIL_BACKEND` | Automatically selected | Optional Django email backend override |
| `DEFAULT_FROM_EMAIL` | SMTP user or local fallback | Sender shown in approval emails |
| `PUBLIC_SITE_URL` | `http://localhost:8000` | Base URL used in chef sign-in links |

### Gmail helper (Windows PowerShell)

```powershell
.\scripts\configure_gmail_email.ps1 `
  -SenderEmail "you@gmail.com" `
  -PublicSiteUrl "http://localhost:8000"
```

The script prompts for a Gmail app password, saves the settings as current-user environment variables, and instructs you to restart your terminal, IDE, and Django server.

### Local development without SMTP

Leave the SMTP username and password unset. Django will use the console email backend, and approval messages will appear in the terminal running `runserver`.

## Data model

### `home.Profile`

- One-to-one relationship with Django's built-in `User`.
- Roles: `User`, `Chef`, and `Admin`.
- Chef approval status and request/approval/removal timestamps.
- Optional references to the administrators who approved or removed the chef.
- Proxy models provide separate admin lists for user and chef profiles.

### `vege.recipe`

- Recipe name.
- Full recipe description.
- Optional image stored under `recipe_images/`.
- Optional author reference to Django's `User`.
- The author is set automatically for newly posted recipes.
- If an author account is later deleted, the recipe remains available with an unknown author.

## Project structure

```text
Savorly/
├── Savorly/                  # Django project configuration
│   ├── settings.py           # Database, email, static/media, security settings
│   ├── urls.py               # Root URL configuration
│   ├── asgi.py               # ASGI entry point
│   └── wsgi.py               # WSGI entry point
├── home/                     # Landing page, authentication, profiles, chef approval
│   ├── admin.py              # User/chef profile administration
│   ├── emails.py             # Chef approval email
│   ├── models.py             # Profile and approval workflow
│   ├── views.py              # Registration, login, logout, health endpoint
│   ├── templates/            # Public and authentication templates
│   ├── static/               # CSS, JavaScript, images, and favicon
│   └── migrations/           # Profile and approval migrations
├── vege/                     # Chef recipe features
│   ├── forms.py              # Recipe create/update form
│   ├── models.py             # Recipe model
│   ├── views.py              # Chef-scoped recipe CRUD
│   ├── templates/            # Add, table, details, and update pages
│   └── migrations/           # Recipe migrations and legacy-owner backfill
├── scripts/
│   └── configure_gmail_email.ps1
├── media/
│   └── recipe_images/        # Uploaded recipe images
├── db.sqlite3                # Local SQLite database
└── manage.py
```

## Testing and validation

Run the complete test suite:

```powershell
python manage.py test
```

Run Django's system checks:

```powershell
python manage.py check
```

Check for missing migrations without writing files:

```powershell
python manage.py makemigrations --check --dry-run
```

The automated tests cover:

- Landing-page links and account choices.
- User registration and login.
- Duplicate usernames and validation failures.
- Chef application, approval, email, removal, and reapplication.
- Role mismatch and administrator login rules.
- Safe post-login redirects and POST-only logout.
- Health endpoint behavior.
- Recipe validation, image-optional creation, listing, and details.
- Thirty-word table previews.
- Recipe ownership enforcement.
- Non-chef access restrictions.

At the time this README was added, all **34 tests** pass, `manage.py check` reports no issues, and no model migrations are missing.

## Current scope and implementation notes

- Recipe browsing and management are implemented for approved chefs only. Regular users can currently register, sign in, and sign out, but do not have implemented favorite-saving, meal-planning, commenting, rating, search, or profile-management screens.
- Public registration supports User and Chef roles only.
- The site uses server-rendered pages; there is no REST or GraphQL API.
- Uploaded media is stored on the local filesystem. Django serves it directly only while `DEBUG=True`.
- Recipe deletion is currently initiated by a direct `GET` link and has no confirmation page. A production-hardening improvement would be a confirmation form using `POST`.
- The checked-in settings are development-oriented: `DEBUG=True`, an empty `ALLOWED_HOSTS`, and a development secret key are hard-coded.

## Production checklist

Before deploying Savorly:

1. Set `DEBUG=False`.
2. Replace `SECRET_KEY` with a secure environment-provided value.
3. Configure `ALLOWED_HOSTS` and HTTPS.
4. Set secure cookie and HTTPS redirect settings.
5. Run `python manage.py migrate` during deployment.
6. Run `python manage.py collectstatic` and serve `staticfiles/` through the web server or CDN.
7. Configure durable media storage if uploads must survive deployment replacement.
8. Set all SMTP variables and use a dedicated transactional email account/provider.
9. Set `PUBLIC_SITE_URL` to the public HTTPS origin.
10. Use a production WSGI/ASGI server and process manager.
11. Review SQLite concurrency and backup requirements, or migrate to a production database.
12. Add confirmation and `POST` handling for destructive actions before public deployment.
