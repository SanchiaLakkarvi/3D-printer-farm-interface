# Supabase Auth owns credentials and sessions

Passwords and sessions are handled by Supabase Auth (`auth.users`). The application `users` profile stores farm identity and Role only, shares the Auth user UUID, and does not keep an `auth_hash`. We rejected app-owned password verification against `users.auth_hash` so we do not invent session/JWT handling and can use the existing Supabase project; FastAPI still enforces authorization from the profile Role.
