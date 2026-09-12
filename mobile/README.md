# Educa — mobile

A Flutter companion to Studio (`../frontend/`): sign up/log in, review a
generated syllabus, edit lesson titles/objectives, approve, and publish —
from a phone. It talks to the same FastAPI backend (`../backend/`) plus
that backend's `/api/auth/*` routes (`../backend/app/auth/`), added
alongside this app.

**Scope cut:** this app does not port the CopilotKit/Agno chat — syllabus
generation and refinement still happen in Studio's chat UI. This app
covers auth plus the review/approve/publish loop, the parts that benefit
most from being on a phone.

## Architecture

Feature-first / layered — Riverpod for state and DI, go_router for
navigation, a repository per feature talking through one shared HTTP
client:

```
lib/
  app.dart                        MaterialApp.router, wires the theme + router

  core/                           Nothing feature-specific lives here
    network/
      api_client.dart             Shared HTTP layer: base URL, bearer token, error mapping
      api_exception.dart
    storage/
      token_storage.dart          JWT persistence via flutter_secure_storage (Keychain/Keystore)
    router/
      app_router.dart             go_router + auth redirect guard (splash/login/signup/course/lesson)
    theme/
      studio_theme.dart           Studio's warm paper/ink tokens (see ../docs/design-system.md)

  features/
    auth/
      domain/app_user.dart        AppUser entity
      data/auth_repository.dart   POST /auth/signup, /auth/login, GET /auth/me
      application/auth_controller.dart   AsyncNotifier<AuthState> — the session; router watches this
      presentation/               login_screen.dart, signup_screen.dart, shared form widgets

    course/
      domain/course.dart          Course/Week/Lesson/LessonContent — mirrors frontend/src/types.ts
      data/course_repository.dart fetchCourse/patchLesson/setApproval/publishLesson/resetCourse
      application/course_controller.dart  AsyncNotifier<Course> — single source of truth for lesson state
      presentation/                course_screen.dart, lesson_screen.dart, status_pill.dart
```

Each feature is data → domain → application → presentation:
repositories only know how to talk to the backend, controllers
(`AsyncNotifier`s) own state and are the only thing screens call into, and
domain classes are plain data with no Flutter/HTTP imports. `core/` holds
what every feature shares (the HTTP client, token storage, theme, router)
— nothing feature-specific belongs there.

Design tokens, fonts, and radii are copied from the **Studio** section of
`../docs/design-system.md`, not the marketing site's dark SaaS look — keep
it that way if you extend this app.

## Auth

- Backend: `POST /api/auth/signup`, `POST /api/auth/login` (both return a
  JWT + user), `GET /api/auth/me`. In-memory user store, PBKDF2 password
  hashing, no external auth dependency — same zero-dependency spirit as
  the course store. See `../backend/app/auth/` and `../docs/README.md`.
  **Additive only**: it doesn't gate `/api/course` or the other existing
  routes, since the React frontend has no auth wiring and gating them
  would break it.
- Client: `AuthController` (`features/auth/application/auth_controller.dart`)
  checks for a stored token on startup, and `core/router/app_router.dart`
  watches it — logged out routes to `/login`/`/signup`, logged in routes
  to `/`. The token lives in the platform Keychain/Keystore via
  `flutter_secure_storage`, not `SharedPreferences`.
- Set `JWT_SECRET` in the backend's `.env` before running this for real
  (see `../backend/.env.example`) — it falls back to an insecure dev
  default otherwise, same pattern as `ANTHROPIC_API_KEY`.

## Run it

Backend first (see `../backend/README` / `../docs/README.md`):

```bash
cd ../backend
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
infisical run --env=dev -- uvicorn app.main:app --reload --port 8000
```

Then:

```bash
flutter pub get
flutter run                 # pick a connected device/simulator
```

The API base URL defaults to `http://localhost:8000/api`, with an
automatic override to `http://10.0.2.2:8000/api` on the Android emulator
(its alias for the host machine). Override explicitly for a physical
device on your LAN or any other setup:

```bash
flutter run --dart-define=API_BASE=http://192.168.1.23:8000/api
```

## Platform notes

- **macOS networking**: the default `flutter create` macOS template only
  grants the `network.server` sandbox entitlement, not `network.client` —
  every outbound request (including Google Fonts' runtime fetch) would
  silently fail with `Operation not permitted`. Both entitlements files
  (`macos/Runner/{DebugProfile,Release}.entitlements`) already have
  `com.apple.security.network.client` added; don't remove it.
- **macOS Keychain, and why `flutter run -d macos` may still fail to
  build here**: `flutter_secure_storage` needs the `keychain-access-groups`
  entitlement on macOS even just to use the app's own private keychain
  (unlike iOS, where a sandboxed app gets its own keychain for free). It's
  present as an **empty array** in both entitlements files — matching the
  package's own example — which is enough at runtime, but Xcode still
  requires the target to be signed with a real development certificate
  the moment *any* keychain entitlement is present, even an empty one.
  If your machine's Xcode isn't signed into an Apple ID yet: Xcode →
  open `macos/Runner.xcworkspace` → Runner target → Signing & Capabilities
  → check "Automatically manage signing" → pick your Apple ID (a free
  Personal Team is enough). One-time, per machine. iOS, Android, and web
  are unaffected — this is a macOS-desktop-only quirk. Verified on an iOS
  simulator instead (see below), where it just works with no extra setup.
- **Android**: `android/app/src/main/AndroidManifest.xml` has an explicit
  `INTERNET` permission. (Debug builds get this for free from Flutter's
  tooling; release builds don't unless it's declared, so it's added here
  directly.)
- **iOS**: no ATS exception needed for `localhost` (Apple exempts loopback
  by default). If you point a physical device at a plain-`http://` LAN IP
  instead, you'll need an `NSAppTransportSecurity` exception domain in
  `ios/Runner/Info.plist` — not added here since it weakens transport
  security and isn't needed for local dev against the simulator.
- **Web** (`flutter run -d chrome`): the backend's CORS allowlist
  (`backend/app/main.py`) currently only includes `http://localhost:5173`
  (Studio's Vite dev server). Add your Flutter web dev origin there if you
  need to run this app in a browser.

## Verified

- `flutter analyze` — no issues.
- `flutter test` — two tests: a splash→login smoke test, and a full
  fake-backend integration test that types credentials into the login
  form, taps "Log in", and asserts it lands on the course screen with the
  fetched course title (`test/auth_flow_test.dart`) — exercises the real
  `AuthController` → `routerProvider` → `CourseController` chain, not just
  widget rendering.
- Backend: `POST /api/auth/signup` → `/login` → `/me`, plus duplicate
  email, wrong password, missing/invalid token — all checked against a
  live `TestClient` (see `../docs/README.md`'s smoke-test pattern).
- `flutter run -d macos`: builds and launches cleanly, confirmed via a
  live run against the real backend.
- `flutter run` on an **iOS simulator**: full app launch, confirmed
  `flutter_secure_storage` actually round-trips through the real
  Keychain (not just the test fakes), and the login screen renders with
  Studio's fonts/colors as designed (verified with a screenshot).
