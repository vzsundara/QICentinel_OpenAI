# Postman Collection

This directory is intentionally empty of Postman collection files.

QI Sentinel currently exposes a Python command-line interface through the `sentinel` command. It does not expose an HTTP or REST API, so there are no endpoints, request bodies, authentication flows, or environment variables that can be represented honestly in Postman.

The supported commands and usage are documented in [`../Src/README.md`](../Src/README.md). Creating placeholder requests would fabricate an interface that the application does not provide.

If an API layer is added in a future approved phase, its versioned API contract should become the source of truth and a synthetic-only Postman collection may then be generated or maintained here. Credentials, production addresses, member data, and other sensitive values must never be included.
