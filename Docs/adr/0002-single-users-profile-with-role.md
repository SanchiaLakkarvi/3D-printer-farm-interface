# Single users profile with Role; no Student/Staff table split

Every person has one `users` row and one Supabase Auth identity. Role is `student`, `farmer`, or `admin` on that row. We rejected separate Student vs Staff tables because Farmers and Admins must still submit print jobs on the same profile (client: one account, hierarchical capabilities). Students self-register via Student Sign-up; Farmers/Admins are Seed Users or Admin-provisioned.
