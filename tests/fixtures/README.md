# Synthetic local TLS fixture

localhost-cert.pem and localhost-key.pem are a public, disposable self-signed test identity
for loopback integration tests, not application credentials. The certificate has localhost and
127.0.0.1 SANs and expires in 2036. Production endpoints never trust this fixture. Tests pass its
certificate explicitly as a CA and retain hostname/TLS verification. No paid/live endpoint is used.
