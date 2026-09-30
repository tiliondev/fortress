# Fortress licensing

Fortress-specific code is licensed by **Tilion Inc.** under the
[Fortress Source Available License 1.1](../LICENSE). The source is available
to read, modify, build, and redistribute subject to that license. This is a
custom source-available license, not an open-source license, and its
production conditions do not automatically expire.

This guide summarizes the license. The terms in [LICENSE](../LICENSE) control.

## What is free?

- **Non-production use at any company size:** development, testing, CI,
  evaluation, proofs of concept, demonstrations, education, and research
  outside live business operations. This stays free whatever your funding or
  revenue, and covers employees, contractors, and service providers doing
  that work for you. No subscription, registration, contact, or payment.
- **Personal, non-commercial use** by an individual not acting for an
  organization.
- **Production use by smaller organizations:** cumulative funding under
  **US$500,000 AND** ARR of **US$300,000 or less**, measured across the
  organization and its controlled group.
- **Production use during a grace period** (see below), for everyone.

Running Fortress requires a licence key. Free users get one in about twenty
seconds by signing in at https://tilion.dev/activate with GitHub, Google, or
an email address; the CLI opens the page for you. The key is checked on your
machine, never online, and the software sends Tilion Inc. nothing about your
use. Activation stores your email, sign-in provider, and the date, and
nothing else. A machine without a key runs for 14 days from first launch so
that every quickstart works immediately. Paying organisations receive their
key at checkout.

## When is a subscription required?

An organization needs one Fortress subscription for production use if
**either**:

- its cumulative funding is **US$500,000 or more**; or
- its annual recurring revenue (ARR) is **more than US$300,000**.

There is one subscription and one price: **US$2,000 per month**, covering the
whole organization with no limit on people, machines, containers, agents, or
browsers. Buy it at **https://tilion.dev/pricing** with a card, bank debit,
bank transfer, or an invoice against a purchase order. No call or email is
needed; the key is issued on payment. Subscriptions run in three-month terms,
renew automatically, and cancel from the billing portal at any time with no
fee. Price or terms can change only with 30 days' notice before a renewal.

## How the licence key works

Every install needs a key. Free and paid keys behave the same way in the
software; only the sign-up path differs.

**Getting a free key.** Run `tilion activate`, or just start Fortress in a
terminal. It prints a short code, opens `https://tilion.dev/activate` in your
browser, and waits. Sign in with GitHub, Google, or an email magic link. The
terminal continues on its own and saves the key to `~/.tilion/license.jwt`.
About twenty seconds, once per machine. `tilion activate --email you@x.com`
sends a magic link instead of opening a browser, and `--print` prints the key
for CI secrets.

**Docker, CI, and agents.** There is no browser, so pass the key as
`TILION_LICENSE_KEY` or mount it at `/run/secrets/tilion_license`. A machine
with no key still runs for 14 days from its first launch, printing a two-line
notice with the activation URL on each start, so every quickstart works the
first time and an agent never has to stop to ask for an email. After day 14
the launcher exits with the URL. The MCP server has an `activate` tool that
returns the URL and code for the human to open.

**Paid keys.** Issued on the checkout confirmation page and by email, and
downloadable from the billing portal. Put it in your secrets manager; one key
covers every host, container, and agent in the organisation.

**What the key is.** A signed token (Ed25519) checked against a public key
built into the launcher and SDKs. Verification is on your machine: no network
call at runtime, no heartbeat, no revocation list. It carries a tier, a hash
of the sign-in email (never the email itself), and an expiry. Free keys last
12 months; from 30 days before expiry, `tilion license refresh` renews it in
one call with no browser, and after expiry the machine is simply back in the
14-day window, so nothing stops on the day. Paid keys expire 45 days after
the subscription term ends, which covers the 30-day lapse grace.

**What Tilion learns.** Per activation: your email, sign-in provider,
provider user id, the date, and IP country. Nothing about launches, hosts,
targets, or usage, ever. The only connections the software makes to Tilion
are obtaining or refreshing a key when you run that command, and downloading
a release from the host you configure.

**Commands.** `tilion activate`, `tilion license status` (tier, expiry, grace
days left), `tilion license refresh`, `tilion license logout`.

**For the team building it.** Three endpoints on `api.tilion.dev`:
`POST /v1/activate/start` returns a device code, user code, and verify URL;
the browser page binds the signed-in identity to the device code;
`POST /v1/activate/poll` returns pending, a token, or expired;
`POST /v1/license/refresh` re-issues a token for the same subject. Token
claims: `sub`, `tier` (free or pro), `email_hash`, `org` (paid only), `iat`,
`exp`, `kid`. The 14-day grace is a build flag, `FORTRESS_KEY_GRACE_DAYS`. The
notice is a plain stderr write from the browser-launch path, never on import
and never through a warnings mechanism. Not built: heartbeat, metering,
telemetry, concurrency caps, or per-licensee builds.

## Grace periods

- **Evaluation:** 15 days of free production use from your first production
  use of a 1.1 release, at any size.
- **Crossing:** 15 days from the end of the month in which you first meet a
  threshold, so a funding round or a revenue milestone is never a same-day
  legal event.
- **Lapse:** 30 days after a failed renewal, still licensed.
- **Transition:** 15 days for anyone running an earlier BSD release in
  production when 1.1 ships.

Every grace period extends while an order is pending.

## Work for clients

If you run Fortress in production for a client, whether as an agency,
contractor, consultant, or outsourcer, both you and the client must be
permitted. Each of you that meets a threshold needs its own subscription,
and either party may buy the client's. Customers of your generally available
product are not tested individually; a dedicated deployment or contracted
automation for a named client is.

## How are the thresholds measured?

The organization and entities it controls, that control it, or under common
control are measured together. An investment fund's other portfolio
companies do not count, and a fiscal sponsor that cannot direct a project
does not count as controlling it. A sole founder's personal projects are
measured alone unless they serve a company the founder controls.

**Funding** is cumulative gross outside funding actually received, including
equity, SAFEs, convertible instruments, debt financing, and business grants.
A revolving or receivables facility counts at its highest balance, not its
cumulative draws. Exactly US$500,000 meets the threshold.

**ARR** is twelve times recurring revenue earned in the last completed
calendar month. One-time fees, collected taxes, and refunds are excluded.
Exactly US$300,000 does not exceed the threshold. Thresholds are measured on
the first day of each month and hold for that month.

| Example | Outcome |
| --- | --- |
| Any company evaluating or testing in a non-production environment | Free |
| Company with US$200,000 funding and US$120,000 ARR running production | Free |
| Company with exactly US$500,000 funding running production | Subscription needed after the 15-day grace periods |
| Bootstrapped company with US$300,001 ARR running production | Subscription needed after the 15-day grace periods |
| Well-funded company running scheduled scraping for internal operations | Subscription needed |
| Agency below the thresholds running a dedicated deployment for a funded client | The client needs the subscription; either party may buy it |
| Individual experimenting on a personal, non-commercial project | Free |

## If you have been running production without a subscription

The license contains a standing settlement offer: the monthly list price for
each month since your grace periods ended, plus 25% if Tilion Inc. raised it
first and nothing extra if you report it yourself within 30 days of noticing,
capped at the 24 months before first notice. Settled use is treated as
permitted from the day it began. Nobody's rights terminate over a shortfall
that is settled.

## Existing versions and third-party software

Earlier BSD-licensed material keeps its BSD permissions; see
[LICENSE-BSD-LEGACY](../LICENSE-BSD-LEGACY). The 1.1 terms cover the
Fortress-specific patches, SDKs, MCP server and launcher, build tooling,
packaging, documentation, and corresponding portions of binaries. Chromium,
bundled fonts, and other third-party materials keep their own licenses and
notices; see [NOTICE](../NOTICE).

## Redistribution, bugs, and contributions

Keep the license and notices in original and modified copies. A rebuild or a
fork keeps the production conditions on the material it contains, and
production use of a rebuild is measured by the same tests.

Fortress does not accept outside contributions. If you find a bug, email
**team@tilion.dev** with the version and steps to reproduce; see
[CONTRIBUTING.md](../CONTRIBUTING.md).
