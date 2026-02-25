Place TLS certificate files here for production proxy:

- `fullchain.pem`
- `privkey.pem`

These are mounted by `docker-compose.prod.yml` into `/etc/nginx/certs/`.
