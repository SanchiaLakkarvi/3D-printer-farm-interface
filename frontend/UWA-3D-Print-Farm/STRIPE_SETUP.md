# Stripe test-mode setup

The checkout endpoint creates a Stripe-hosted payment page. The secret key is
read only on the server and must never be committed.

1. Copy your Stripe test secret key from the Stripe Dashboard.
2. Add it to your local environment as `STRIPE_SECRET_KEY`.
3. Add the same variable to the hosting environment before deployment.
4. Use Stripe test cards while the key begins with `sk_test_`.

The current demonstration price is AUD $11.73 for a 4-hour-22-minute print:
$5.00 for the first hour plus $2.00 per additional hour.
