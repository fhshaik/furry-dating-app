# FurConnect — Product Requirements Document

## Overview

FurConnect is a production-ready furry dating and social app where users create fursona profiles, discover other furs via swipe-based matching, and form or join polygamous "pack" groups. Think Tinder meets found-family dynamics for the furry community.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite (SPA) |
| Backend | FastAPI (Python 3.12) |
| Database | MySQL 8 |
| Auth | OAuth 2.0 — Google + Discord |
| Image Storage | AWS S3 |
| Real-time | WebSockets (FastAPI native) |
| Containerization | Docker + Docker Compose |
| Reverse Proxy | Nginx |
| Deployment Target | AWS EC2 |

---

## Architecture

```
┌─────────────────────────────────────────┐
│              EC2 / Docker Host           │
│                                          │
│  ┌──────────┐     ┌──────────────────┐  │
│  │  Nginx   │────▶│  Frontend (React) │  │
│  │ :80/:443 │     │  Vite SPA build   │  │
│  └──────────┘     └──────────────────┘  │
│       │                                  │
│       ▼                                  │
│  ┌──────────────────────────────────┐   │
│  │     Backend (FastAPI :8000)       │   │
│  │  - REST API + WebSocket           │   │
│  │  - OAuth handler (Google/Discord) │   │
│  │  - S3 presigned URL generator     │   │
│  └──────────────┬───────────────────┘   │
│                 │ internal network       │
│  ┌──────────────▼───────────────────┐   │
│  │   MySQL (local) / RDS (prod)      │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘

S3 Bucket (external) ◀── presigned upload URLs
```

---

## Core Features (MVP)

### 1. Authentication (OAuth)
- Sign in via Google or Discord
- JWT tokens stored in httpOnly cookies
- Token refresh flow
- Logout / revoke session

### 2. User Profile
- One account per OAuth identity
- Display name, bio, location (city/region), age
- NSFW content preference toggle (with age gate)
- Orientation / relationship style tags

### 3. Fursonas
- Multiple fursonas per user (up to 5)
- Each fursona has: name, species, personality traits, description
- Image upload (reference sheets / avatar) → AWS S3
- Mark one as "primary" fursona shown in discovery
- Species tag library (wolf, fox, dragon, husky, etc.)
- NSFW fursona flag (only visible to users with NSFW enabled)

### 4. Discovery — Swipe Mode
- Card stack showing other users' primary fursona
- Swipe right = like, swipe left = pass
- Mutual like → creates a 1:1 Match
- Filter by: species, distance (city), age range, relationship style
- Skip already-seen profiles

### 5. Packs (Group Matching)
- Any user can create a Pack with: name, description, max size, open/closed status
- Pack has a fursona (species tags, image, bio)
- Pack members invite others OR set pack as discoverable
- Swipe mode for packs: swipe on a pack card to request joining
- Pack admins approve/deny join requests
- All pack members must approve a new member (consensus join) OR admin-only approval (pack setting)
- Pack chat room (WebSocket)

### 6. Matching & Connections
- 1:1 matches from mutual individual swipes
- Pack membership (multi-member relationship)
- Match feed showing all active matches and packs
- Unmatch / leave pack

### 7. Real-time Messaging (WebSocket)
- 1:1 chat between matched users
- Group chat inside each pack
- Message history persisted in MySQL
- Read receipts (seen/unseen)
- Text only for MVP (no image messages yet)

### 8. Notifications (in-app only, MVP)
- New match
- Pack join request (for admins)
- New message (badge count)

---

## API Endpoints

### Health
- `GET /api/health` — app liveness check
- `GET /api/health/db` — database connectivity check

### Auth
- `GET /api/auth/google` — redirect to Google OAuth
- `GET /api/auth/google/callback` — Google OAuth callback
- `GET /api/auth/discord` — redirect to Discord OAuth
- `GET /api/auth/discord/callback` — Discord OAuth callback
- `POST /api/auth/logout` — invalidate session
- `GET /api/auth/me` — get current user

### Users
- `GET /api/users/:id` — get public profile
- `PATCH /api/users/me` — update own profile
- `DELETE /api/users/me` — delete account

### Fursonas
- `GET /api/fursonas` — list own fursonas
- `POST /api/fursonas` — create fursona
- `PATCH /api/fursonas/:id` — update fursona
- `DELETE /api/fursonas/:id` — delete fursona
- `POST /api/fursonas/:id/primary` — set as primary
- `GET /api/fursonas/:id/upload-url` — get S3 presigned upload URL

### Discovery
- `GET /api/discover` — get next swipe card(s) (paginated, filtered)
- `POST /api/swipes` — record swipe action (like/pass, target: user or pack)

### Matches
- `GET /api/matches` — list all 1:1 matches
- `DELETE /api/matches/:id` — unmatch

### Packs
- `GET /api/packs` — list packs (discover or own)
- `POST /api/packs` — create pack
- `GET /api/packs/:id` — get pack details
- `PATCH /api/packs/:id` — update pack (admin only)
- `DELETE /api/packs/:id` — disband pack (admin only)
- `POST /api/packs/:id/join-request` — request to join
- `GET /api/packs/:id/join-requests` — list pending requests (admin)
- `PATCH /api/packs/:id/join-requests/:userId` — approve/deny
- `DELETE /api/packs/:id/members/:userId` — remove member / leave

### Messaging
- `GET /api/conversations` — list all conversations (1:1 and pack)
- `GET /api/conversations/:id/messages` — get message history
- `WS /ws/chat/:conversationId` — WebSocket chat connection

### Items (CRUD example / admin reference)
- `GET /api/items`
- `POST /api/items`
- `GET /api/items/:id`
- `PATCH /api/items/:id`
- `DELETE /api/items/:id`

---

## Database Schema (Key Tables)

```
users               — id, oauth_provider, oauth_id, email, display_name, bio, age, city, nsfw_enabled, created_at
fursonas            — id, user_id, name, species, traits (JSON), description, image_url, is_primary, is_nsfw, created_at
species_tags        — id, name, slug
swipes              — id, swiper_id, target_user_id, target_pack_id, action (like/pass), created_at
matches             — id, user_a_id, user_b_id, created_at, unmatched_at
packs               — id, creator_id, name, description, image_url, species_tags (JSON), max_size, consensus_required, is_open, created_at
pack_members        — pack_id, user_id, role (admin/member), joined_at
pack_join_requests  — id, pack_id, user_id, status (pending/approved/denied), created_at
conversations       — id, type (direct/pack), pack_id, created_at
conversation_members — conversation_id, user_id
messages            — id, conversation_id, sender_id, content, sent_at, is_read
```

---

## Environment Variables

```env
# Auth
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
DISCORD_CLIENT_ID=
DISCORD_CLIENT_SECRET=
JWT_SECRET=
FRONTEND_URL=

# Database
MYSQL_HOST=
MYSQL_PORT=3306
MYSQL_USER=
MYSQL_PASSWORD=
MYSQL_DATABASE=

# S3
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_S3_BUCKET=
AWS_REGION=

# App
ENVIRONMENT=development
```

---

## File Structure (Target)

```
furry-dating-app/
├── PRD.md
├── .env.example
├── docker-compose.local.yml
├── docker-compose.prod.yml
│
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── router.tsx
│       ├── components/
│       ├── pages/
│       ├── hooks/
│       ├── store/
│       └── api/
│
└── backend/
    ├── Dockerfile
    ├── requirements.txt
    ├── alembic.ini
    ├── alembic/
    └── app/
        ├── main.py
        ├── config.py
        ├── database.py
        ├── models/
        ├── schemas/
        ├── routers/
        ├── services/
        ├── auth/
        └── websocket/
```

---

## Task Checklist

### Phase 1 — Project Scaffolding & Infrastructure

#### Docker & DevOps
- [x] Create root `.env.example` with all required variables
- [x] Create `docker-compose.local.yml` with frontend, backend, mysql services and named volume
- [x] Create `docker-compose.prod.yml` with frontend and backend only (external RDS)
- [x] Write backend `Dockerfile` with multi-stage build, non-root user, and healthcheck
- [x] Write frontend `Dockerfile` with multi-stage build (node build → nginx serve)
- [x] Configure `nginx.conf` for SPA fallback routing and `/api` proxy pass

#### Backend Foundation
- [x] Initialize FastAPI app with CORS, lifespan, and structured logging
- [x] Create `config.py` using `pydantic-settings` to load all env vars
- [x] Set up SQLAlchemy async engine with MySQL connection via env vars
- [x] Create Alembic migration setup and initial migration file
- [x] Add `GET /api/health` endpoint returning app status
- [x] Add `GET /api/health/db` endpoint that runs a test DB query
- [x] Create generic `/api/items` CRUD router as reference implementation

#### Frontend Foundation
- [x] Scaffold Vite + React + TypeScript project
- [x] Install and configure React Router v6 with SPA fallback
- [x] Set up Tailwind CSS (or preferred CSS framework)
- [x] Configure Axios (or fetch wrapper) with base URL from env var
- [x] Create basic layout shell (header, main, nav)
- [x] Add 404 / not-found fallback page

---

### Phase 2 — Authentication

#### Backend Auth
- [x] Install and configure `authlib` for OAuth 2.0
- [x] Create Google OAuth redirect and callback endpoints
- [x] Create Discord OAuth redirect and callback endpoints
- [x] Create `User` model with `oauth_provider`, `oauth_id`, `email`, `display_name` fields
- [x] Add upsert logic: find-or-create user on OAuth callback
- [x] Generate signed JWT on successful OAuth login
- [x] Store JWT in httpOnly cookie on callback response
- [x] Create `GET /api/auth/me` endpoint returning current user
- [x] Create `POST /api/auth/logout` endpoint clearing cookie
- [x] Write `get_current_user` FastAPI dependency for protected routes
- [x] Add age gate check — require `age` confirmed before accessing NSFW content

#### Frontend Auth
- [x] Create `AuthContext` providing current user state and login/logout actions
- [x] Create Login page with "Sign in with Google" and "Sign in with Discord" buttons
- [x] Handle OAuth redirect flow (post-callback token fetch)
- [x] Create protected route wrapper component
- [x] Create `useCurrentUser` hook
- [x] Add logout button in header with redirect to login page

---

### Phase 3 — User Profiles & Fursonas

#### Backend
- [x] Create `User` profile fields: `bio`, `age`, `city`, `nsfw_enabled`, `relationship_style`
- [x] Create `PATCH /api/users/me` endpoint for profile updates
- [x] Create `GET /api/users/:id` public profile endpoint
- [x] Create `DELETE /api/users/me` account deletion endpoint
- [x] Create `Fursona` model with all fields (name, species, traits JSON, description, image_url, is_primary, is_nsfw)
- [x] Create `GET /api/fursonas` — list own fursonas
- [x] Create `POST /api/fursonas` — create new fursona
- [x] Create `PATCH /api/fursonas/:id` — update fursona (owner only)
- [x] Create `DELETE /api/fursonas/:id` — delete fursona (owner only)
- [x] Create `POST /api/fursonas/:id/primary` — set fursona as primary
- [x] Create `GET /api/fursonas/:id/upload-url` — generate S3 presigned PUT URL
- [x] Create species tag seed data and `GET /api/species` endpoint
- [x] Enforce max 5 fursonas per user

#### Frontend
- [x] Create Profile Edit page (display name, bio, age, city, relationship style)
- [x] Add NSFW toggle with age confirmation modal
- [x] Create Fursona Manager page listing all fursonas
- [x] Build Fursona Create/Edit form (name, species dropdown, traits multi-select, description)
- [x] Implement S3 image upload flow: fetch presigned URL → PUT to S3 → save URL to fursona
- [x] Show fursona image preview after upload
- [x] Add "Set as Primary" button per fursona card
- [x] Enforce 5-fursona limit in UI

---

### Phase 4 — Discovery & Swiping

#### Backend
- [x] Create `Swipe` model (swiper_id, target_user_id, target_pack_id, action)
- [x] Create `Match` model (user_a_id, user_b_id, created_at, unmatched_at)
- [x] Create `GET /api/discover` returning paginated swipe candidates (exclude already-seen, self, existing matches)
- [x] Apply filters: species, city, age range, relationship style, NSFW setting
- [x] Create `POST /api/swipes` to record like/pass action
- [x] On mutual like (user→user): auto-create Match and trigger notification
- [x] Create `GET /api/matches` listing all active 1:1 matches
- [x] Create `DELETE /api/matches/:id` unmatch endpoint

#### Frontend
- [x] Create Discover page with swipe card stack UI
- [x] Build SwipeCard component showing fursona image, name, species, traits
- [x] Add swipe left (pass) and swipe right (like) gesture/button controls
- [x] Animate card transition on swipe
- [x] Show "It's a Match!" overlay on mutual like
- [x] Build filter drawer: species multi-select, age range slider, city input
- [x] Create Matches page listing all 1:1 matches with last message preview

---

### Phase 5 — Packs (Group Matching)

#### Backend
- [x] Create `Pack` model with all fields
- [x] Create `PackMember` model (pack_id, user_id, role)
- [x] Create `PackJoinRequest` model (pack_id, user_id, status)
- [x] Create `POST /api/packs` — create pack (creator auto-joins as admin)
- [x] Create `GET /api/packs` — list discoverable packs (with filters)
- [x] Create `GET /api/packs/:id` — pack detail
- [x] Create `PATCH /api/packs/:id` — update pack (admin only)
- [x] Create `DELETE /api/packs/:id` — disband pack (admin only, removes all members)
- [x] Allow swiping on packs via existing `POST /api/swipes` (target_pack_id)
- [x] Create `POST /api/packs/:id/join-request` — request to join open pack
- [x] Create `GET /api/packs/:id/join-requests` — list pending requests (admin only)
- [x] Create `PATCH /api/packs/:id/join-requests/:userId` — approve or deny request
- [x] Implement consensus approval: if pack setting requires all members to approve, track votes
- [x] Create `DELETE /api/packs/:id/members/:userId` — leave or remove member
- [x] Enforce max pack size from pack settings

#### Frontend
- [x] Add "Packs" tab to Discover page showing swipeable pack cards
- [x] Build PackCard component (pack image, name, member count, species tags)
- [x] Create Pack Detail page (members list, description, join button)
- [x] Create Pack Create/Edit form
- [x] Create My Packs page listing packs user belongs to
- [x] Build Pack Admin panel: pending join requests, approve/deny, member list, remove member
- [x] Show consensus vote status for join requests when applicable

---

### Phase 6 — Real-time Messaging

#### Backend
- [x] Create `Conversation` model (type: direct/pack, optional pack_id)
- [x] Create `ConversationMember` model
- [x] Create `Message` model (conversation_id, sender_id, content, sent_at, is_read)
- [x] Auto-create direct conversation on match creation
- [x] Auto-create pack conversation on pack creation
- [x] Create `GET /api/conversations` listing all user conversations
- [x] Create `GET /api/conversations/:id/messages` for message history (paginated)
- [x] Implement `WS /ws/chat/:conversationId` WebSocket endpoint
- [x] WebSocket auth: validate JWT from query param or cookie on connect
- [x] Broadcast messages to all connected members of a conversation
- [x] Persist messages to DB on send
- [x] Mark messages as read when recipient receives them

#### Frontend
- [x] Create Inbox page listing all conversations (direct + pack)
- [x] Build ConversationView component with message list and input
- [x] Implement WebSocket client connection with reconnect logic
- [x] Render incoming messages in real time
- [x] Show read receipts (seen indicator)
- [x] Display unread message badge count in nav
- [x] Create useWebSocket hook managing connection lifecycle

---

### Phase 7 — Notifications (In-App)

#### Backend
- [x] Create `Notification` model (user_id, type, payload JSON, is_read, created_at)
- [x] Emit notifications on: new match, pack join request received, new message (if not in conversation)
- [x] Create `GET /api/notifications` endpoint (unread first, paginated)
- [x] Create `PATCH /api/notifications/:id/read` mark as read
- [x] Create `PATCH /api/notifications/read-all` mark all read

#### Frontend
- [x] Create Notifications bell icon in header with unread count badge
- [x] Build Notifications dropdown/page listing recent notifications
- [x] Poll or use WebSocket channel for real-time notification count updates
- [x] On click: navigate to relevant match, pack, or conversation

---

### Phase 8 — Polish & Production Readiness

- [x] Add rate limiting to all public endpoints (slowapi or similar)
- [x] Add input validation and sanitization on all write endpoints
- [x] Implement NSFW content gating: hide NSFW fursonas from users without nsfw_enabled
- [x] Add content moderation hooks (report user / report content endpoints)
- [x] Write Alembic migrations for all models in correct dependency order
- [x] Seed database with sample species tags
- [x] Add structured JSON logging to backend
- [x] Set up Sentry error tracking (optional, env-gated)
- [x] Write minimal README with local dev setup, env var reference, and deploy instructions
- [x] Verify docker-compose.local.yml full stack starts cleanly
- [x] Verify docker-compose.prod.yml connects to external MySQL correctly
- [x] Test Nginx SPA routing fallback for client-side routes
- [x] Confirm no secrets hardcoded anywhere in codebase
- [x] Confirm MySQL port is not exposed in any Docker config

---

## Out of Scope (Post-MVP)

- Push notifications (FCM/APNs)
- Video profiles
- Image messages in chat
- Paid subscription / premium tiers
- Location-based GPS matching (city-level only for MVP)
- Mobile app (React Native)
- AI-based match recommendations
