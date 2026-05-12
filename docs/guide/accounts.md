---
title: Accounts & credits
description: Sign-up, sign-in (password or magic link), credit balance, and the unlimited tier.
---

# Accounts & credits

You can search **without** an account by paying £1 (or £3 for director
searches) per query. An account exists mainly so that you can hold a credit
balance and avoid going through Stripe for every search.

## Sign up

Go to [`/auth`](https://landregistry.company/auth) and enter an email
address. You can either:

- Set a password — useful if you want classic sign-in.
- Skip the password — we'll send you a **magic link** instead.

On your first sign-in you receive **10 free credits**.

## Sign in

Two options, side by side on `/auth`:

- **Password** — email + password.
- **Magic link** — enter your email, click the link in the inbox.
  No password needed.

Sessions are stored in a secure HTTP-only cookie. Sign out from any page
that shows the navbar credit pill.

## Credit balance

The navbar shows your current credit balance with a small star icon:

```
⭐ 10
```

A search **deducts credits** if you have enough; otherwise the
search prompts for a one-off Stripe payment. The costs are:

| Search type             | Credits |
| ----------------------- | ------- |
| Company (name or CRN)   | 1       |
| Address / postcode      | 1       |
| Director                | 3       |

Every deduction is recorded in a `credit_transactions` audit row.

## Top up

There is no fixed top-up bundle in the UI — instead, **every search you pay
for** via Stripe counts as a one-off charge for that single query. If you
want to buy credits in bulk, [contact us](mailto:hello@inteltree.co.uk).

## Unlimited tier

A small number of friends-and-family accounts are flagged
`is_unlimited = true`. These see an infinity badge in the navbar and
bypass the credit check entirely. There is no public way to upgrade —
the flag is set manually.

## Forgotten password

From `/auth`, click **Forgot password** and submit your email. You'll be
sent a single-use reset token that expires after one hour. Magic links
work as a faster alternative.

## Account deletion

Email us at **hello@inteltree.co.uk** to delete your account. Search
history is not stored, but credit-transaction audit rows are retained
for accounting purposes for 6 years (UK statutory minimum).

## Next

- [Pricing](/guide/pricing) — the full cost table and refund policy.
- [API authentication](/api/authentication) — using your account from code.
