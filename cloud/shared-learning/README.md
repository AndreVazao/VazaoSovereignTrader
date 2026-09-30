
## Device key policy

Device registration accepts Ed25519, RSA with a modulus of at least 2048 bits, and EC keys on `prime256v1` or `secp384r1`. Public keys are canonicalized before their SHA-256 fingerprint is stored. This validates key format/strength only; it does not prove possession or approve the device.

